"""Project review regressions with archived replies or an offline model transport."""
import json
from pathlib import Path

import httpx
import pytest
from fastapi.testclient import TestClient

from app.core.llm_client import GenericLLMClient, LLMClientConfig, LLMResponse
from app.workbench import create_workbench

R8_RESULTS = (
    Path(__file__).parents[1] / "docs/evidence/studio-r8/live-main/results.json"
)


class RecordedModel:
    def __init__(self, response):
        self.response = response

    async def chat(self, messages, **kwargs):
        return LLMResponse(content=json.dumps(self.response), model="offline-replay")


def project(client):
    client.post("/api/session")
    row = client.post("/api/projects", json={"name": "quality regression"}).json()
    base = f"/api/projects/{row['id']}"
    client.post(base + "/privacy", json={"allow_external": True})
    return base


def review(body, response, *, stream=False):
    with TestClient(create_workbench(model=RecordedModel(response))) as client:
        base = project(client)
        if stream:
            events = client.post(base + "/review-stream", json=body).text.splitlines()
            return json.loads(events[-1])["data"]
        return client.post(base + "/review", json=body).json()


def archived(case_id):
    row = next(
        row for row in json.loads(R8_RESULTS.read_text(encoding="utf-8"))
        if row["case_id"] == case_id
    )
    return (
        {"files": row["files"], "path": "main.py", "revision": 0, "request": row["request"]},
        row["result"]["review"],
    )


def test_scope_shadow_withholds_historical_constant_zero_patch_and_wrong_hint():
    body, response = archived("scope-shadow")
    result = review(body, response, stream=True)
    assert result["status"] == "accepted"
    assert result["claim_status"] == "unverified"
    assert result["patch_check"]["status"] == "withheld"
    assert result["patch_check"]["reason"] == "reference-mismatch"
    assert result["review"]["patches"] == []
    assert "return total_sum" not in json.dumps(result["review"], ensure_ascii=False)
    assert "sum(values)" in result["review"]["hints"][0]


def test_minimal_shadowing_removal_has_finite_sum_evidence_and_still_requires_approval():
    body, response = archived("scope-shadow")
    response["patches"] = [{
        "path": "main.py", "line": 2, "before": "    sum = 0", "after": "",
        "reason": "恢复内置求和函数的名字绑定。",
    }]
    result = review(body, response)
    assert result["teaching_source"] == "local-static-rule"
    assert result["claim_status"] == "unverified"
    assert result["review"]["patches"] == response["patches"]
    assert result["patch_check"] == {
        "status": "sampled", "reason": "sum-reference-samples", "samples": [
            {"input": [], "reference": 0, "candidate": 0},
            {"input": [2, 3], "reference": 5, "candidate": 5},
            {"input": [-4, 2], "reference": -2, "candidate": -2},
        ],
    }


def test_correct_accumulator_cannot_teach_that_integer_zero_concatenates_strings():
    body, response = archived("correct-scope")
    result = review(body, response)
    assert result["status"] == "accepted"
    assert result["claim_status"] == "unverified"
    explanation = result["review"]["explanation"]
    assert "TypeError" in explanation
    assert "会得到拼接结果" not in explanation
    assert not result["review"]["patches"]


def test_correct_accumulator_withholds_return_zero_after_valid_accumulation():
    body, response = archived("correct-scope")
    response["patches"] = [{
        "path": "main.py", "line": 5, "before": "    return result",
        "after": "    return 0", "reason": "修改累加后的返回值。",
    }]
    result = review(body, response)
    assert result["status"] == "accepted"
    assert result["claim_status"] == "unverified"
    assert result["patch_check"]["status"] == "withheld"
    assert result["patch_check"]["reason"] == "accumulator-regression"
    assert result["patch_check"]["samples"][-1] == {
        "input": [2, 3], "reference": 5, "candidate": 0,
    }
    assert result["review"]["patches"] == []


def test_correct_accumulator_withholds_regression_even_when_cursor_is_on_caller():
    body, response = archived("correct-scope")
    body["files"]["main.py"] += "\nprint(total([2, 3]))\n"
    body["cursor_line"] = 7
    response["patches"] = [{
        "path": "main.py", "line": 5, "before": "    return result",
        "after": "    return 0", "reason": "修改返回值。",
    }]
    result = review(body, response)
    assert result["patch_check"]["reason"] == "accumulator-regression"
    assert result["review"]["patches"] == []


def test_accumulator_complexity_question_retains_answer_while_correcting_false_claim():
    body, response = archived("correct-scope")
    body["request"] = "请详细分析时间复杂度和额外空间复杂度，说明原因。"
    response["explanation"] += " 时间 O(n)，空间 O(1)。"
    result = review(body, response)
    assert result["teaching_source"] == "local-static-rule"
    assert "TypeError" in result["review"]["explanation"]
    assert "会得到拼接结果" not in result["review"]["explanation"]
    mechanism = result["review"]["teaching"]["mechanism"]
    assert "O(n)" in mechanism and "O(1)" in mechanism
    assert "遍历" in mechanism and "累加器" in mechanism


def test_complete_bool_function_confirms_fallthrough_none_without_claiming_execution():
    body, response = archived("return-none")
    result = review(body, response)
    assert result["status"] == "accepted"
    assert result["claim_status"] == "unverified"
    assert "positive(0)" in result["review"]["teaching"]["example"]
    assert "隐式返回 None" in result["review"]["explanation"]
    assert "静态" in result["review"]["teaching"]["example"]
    assert "后续" not in result["review"]["teaching"]["uncertainty"]


def test_partial_file_does_not_trigger_complete_function_teaching():
    body, response = archived("return-none")
    body["files"]["main.py"] += "# filler\n" * 30 + "    return False\n"
    result = review(body, response)
    assert result["status"] == "accepted"
    assert "teaching_source" not in result
    assert result["review"]["explanation"] == response["explanation"]


def test_fallthrough_fix_cannot_reverse_existing_positive_return():
    body, response = archived("return-none")
    response["patches"] = [{
        "path": "main.py", "line": 4, "before": "        return True",
        "after": "        return False", "reason": "调整布尔返回值。",
    }]
    result = review(body, response)
    assert result["patch_check"]["reason"] == "existing-branch-regression"
    assert result["review"]["patches"] == []


def patch_response(before, after):
    return {
        "explanation": "请检查输出约定。",
        "hints": ["用已知输入对照输出。"],
        "citations": [{"path": "main.py", "line": 1, "quote": before}],
        "patches": [{
            "path": "main.py", "line": 1, "before": before,
            "after": after, "reason": "修改候选",
        }],
    }


@pytest.mark.parametrize(("before", "after", "status", "reason"), [
    ("print(1)", "print([][0])", "withheld", "new-runtime-error"),
    ("print(1)", "print(1", "withheld", "candidate-syntax-error"),
    ("print(1)", "print(2)", "review-required", "output-changed"),
    ("print(1)", "for x in [1]:\n    print(x)", "unknown", "unsupported"),
    ("print(1)", "print(1 + 0)", "sampled", "same-observed-output"),
])
def test_candidate_compares_existing_entry_in_bounded_interpreter(before, after, status, reason):
    result = review(
        {"files": {"main.py": before}, "path": "main.py", "revision": 0},
        patch_response(before, after),
    )
    assert result["claim_status"] == "unverified"
    assert result["patch_check"]["status"] == status
    assert result["patch_check"]["reason"] == reason
    assert bool(result["review"]["patches"]) == (status not in {"withheld", "unknown"})


@pytest.mark.parametrize(("entry", "helper", "import_line"), [
    ("main.py", "helpers.py", "from helpers import normalize as clean"),
    ("pkg/main.py", "pkg/helpers.py", "from .helpers import normalize as clean"),
])
def test_native_tools_read_exact_virtual_helper_and_update_coverage(entry, helper, import_line):
    files = {
        entry: f"{import_line}\nprint(clean(2))",
        helper: "# filler\n" * 25 + "def normalize(x):\n    return x + 1",
        "decoy.py": "def normalize(x):\n    return 999",
    }
    request = {"files": files, "path": entry, "revision": 0, "cursor_line": 2}
    received = []

    def provider(wire_request):
        payload = json.loads(wire_request.content)
        received.append(payload)
        if len(received) == 1:
            initial = json.loads(payload["messages"][-1]["content"])
            assert initial["source_coverage"][helper]["complete"] is False
            assert all(snippet["path"] != "decoy.py" for snippet in initial["snippets"])
            message = {"tool_calls": [{
                "id": "read_helper", "type": "function",
                "function": {
                    "name": "get_current_file",
                    "arguments": json.dumps({"path": helper, "start_line": 1, "end_line": 27}),
                },
            }]}
            finish = "tool_calls"
        else:
            tool = json.loads(payload["messages"][-1]["content"])
            assert tool["status"] == "ok"
            assert tool["source_coverage"][helper] == {"total_lines": 27, "complete": True}
            assert tool["snippets"][0] == {"path": helper, "line": 1, "quote": "# filler"}
            answer = {"explanation": "源码绑定到项目内函数。", "hints": ["查看返回值。"],
                      "citations": [tool["snippets"][0]]}
            message = {"content": json.dumps(answer)}
            finish = "stop"
        return httpx.Response(200, json={
            "model": "offline", "choices": [{"index": 0, "finish_reason": finish,
                                             "message": {"role": "assistant", **message}}],
        })

    model = GenericLLMClient(
        LLMClientConfig(model_name="offline", base_url="https://example.test/v1", api_key="test"),
        transport=httpx.MockTransport(provider),
    )
    with TestClient(create_workbench(model=model)) as client:
        base = project(client)
        events = client.post(base + "/review-stream", json=request).text.splitlines()
        result = json.loads(events[-1])["data"]
    assert result["status"] == "accepted"
    assert result["model_turns"] == 2
    assert result["tool_trace"][0]["status"] == "ok"


def test_stale_revision_verify_does_not_replace_current_execution_or_add_history():
    with TestClient(create_workbench()) as client:
        base = project(client)
        current = {"files": {"main.py": "print(2)"}, "path": "main.py", "revision": 1}
        assert client.post(base, json={"files": current["files"], "revision": 0}).status_code == 200
        assert client.post(base + "/verify", json=current).json()["stdout"] == "2\n"
        assert client.post(base + "/verify", json={
            **current, "files": {"main.py": "print(1)"}, "revision": 0,
        }).status_code == 409
        history = client.get(base + "/learning").json()["items"]
        executions = [item for item in history if item["source"] == "restricted-ast-interpreter"]
        assert [item["revision"] for item in executions] == [1]


def test_execution_tool_does_not_return_another_entry_with_identical_buffer():
    observed = []

    def provider(request):
        messages = json.loads(request.content)["messages"]
        if messages[-1]["role"] == "tool":
            observed.append(json.loads(messages[-1]["content"]))
            citation = json.loads(messages[1]["content"])["snippets"][0]
            message = {"content": json.dumps({
                "explanation": "请验证当前入口。", "hints": ["运行入口后检查结果。"],
                "citations": [citation],
            })}
            finish = "stop"
        else:
            message = {"tool_calls": [{
                "id": "execution", "type": "function",
                "function": {"name": "get_execution_result", "arguments": "{}"},
            }]}
            finish = "tool_calls"
        return httpx.Response(200, json={
            "model": "offline", "choices": [{"index": 0, "finish_reason": finish,
                                             "message": {"role": "assistant", **message}}],
        })

    model = GenericLLMClient(
        LLMClientConfig(model_name="offline", base_url="https://example.test/v1", api_key="test"),
        transport=httpx.MockTransport(provider),
    )
    with TestClient(create_workbench(model=model)) as client:
        base = project(client)
        body = {
            "files": {"main.py": "print(1)", "other.py": "print(2)"},
            "path": "main.py", "revision": 0, "use_tools": True,
        }
        assert client.post(base + "/verify", json={
            "files": body["files"], "path": "other.py", "revision": 0,
        }).json()["stdout"] == "2\n"
        assert client.post(base + "/review", json=body).json()["status"] == "accepted"
        assert client.post(base + "/verify", json={
            "files": body["files"], "path": body["path"], "revision": 0,
        }).json()["stdout"] == "1\n"
        assert client.post(base + "/review", json=body).json()["status"] == "accepted"
    assert observed[0]["status"] == "not-run"
    assert observed[1]["status"] == "ok"
    assert observed[1]["result"]["entry_path"] == "main.py"
    assert observed[1]["result"]["stdout"] == "1\n"

def test_added_false_else_is_not_reported_as_reversing_positive_branch():
    body, response = archived('return-none')
    response['patches'] = [{'path':'main.py','line':4,'before':'        return True',
        'after':'        return True\n    else:\n        return False','reason':'补全布尔返回'}]
    result=review(body,response)
    assert result['patch_check']['reason'] != 'existing-branch-regression'
    assert result['claim_status'] == 'unverified'

def test_unexecuted_function_change_has_no_comparable_behavior():
    files={'main.py':'def unused(x):\n    return x\nprint(1)'}
    response={'explanation':'检查候选','hints':['核对输入'],'citations':[{'path':'main.py','line':2,'quote':'    return x'}],
              'patches':[{'path':'main.py','line':2,'before':'    return x','after':'    return 0','reason':'候选'}]}
    result=review({'files':files,'path':'main.py','revision':0},response)
    assert result['patch_check']['reason']=='no-observed-output'
    assert result['review']['patches']==[]


@pytest.mark.parametrize('default', ['0', '1', 'False'])
def test_removing_none_error_does_not_establish_missing_return_contract(default):
    files = {'main.py': 'def price(flag):\n    if flag:\n        return 2\nprint(price(False) + 5)\n'}
    response = {
        'explanation': '假分支隐式返回 None，默认值需要确认。', 'hints': ['确认业务默认值。'],
        'citations': [{'path': 'main.py', 'line': 3, 'quote': '        return 2'}],
        'patches': [{'path': 'main.py', 'line': 3, 'before': '        return 2',
                     'after': f'        return 2\n    return {default}', 'reason': '候选默认值'}],
    }
    result = review({'files': files, 'path': 'main.py', 'revision': 0}, response)
    assert result['patch_check']['reason'] == 'return-contract-unconfirmed'
    assert result['claim_status'] == 'unverified'
    assert result['review']['patches'] == []
