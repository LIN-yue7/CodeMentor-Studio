
import asyncio
import json

from fastapi.testclient import TestClient

from app.core.llm_client import LLMResponse
from app.workbench import create_workbench
from tests.test_workbench_flow import diagnose


class StubModel:
    def __init__(self, line=3, citations=None, timeout=False):
        self.line = line
        self.citations = citations or ["loop-boundary-range-v1"]
        self.timeout = timeout
        self.messages = []

    async def chat(self, messages, **kwargs):
        self.messages = messages
        if self.timeout:
            raise asyncio.TimeoutError
        return LLMResponse(content=json.dumps({"evidence_id": "local:loop-boundary", "line": self.line,
                                                "citations": self.citations,
                                                "explanation": "检查 range 的右端点。"}), model="stub")


def test_retrieval_reaches_model_and_only_retrieved_ids_can_be_rendered():
    model = StubModel()
    with TestClient(create_workbench(model=model)) as client:
        client.post("/api/session")
        result = diagnose(client)
        assert result["mode"] == "simulated"
        assert result["model_status"] == "accepted"
        assert result["annotation"]["citations"] == ["loop-boundary-range-v1"]
        assert result["cards"][0]["id"] == "loop-boundary-range-v1"
        assert "loop-boundary-range-v1" in model.messages[-1].content
        assert [event["stage"] for event in result["events"]] == ["analysis", "retrieval", "model", "practice"]


def test_model_failure_and_bad_citations_do_not_block_local_workflow():
    for model, expected in (
        (StubModel(line=4), "invalid"),
        (StubModel(citations=["invented"]), "invalid"),
        (StubModel(timeout=True), "timeout"),
    ):
        with TestClient(create_workbench(model=model)) as client:
            client.post("/api/session")
            result = diagnose(client)
            assert result["model_status"] == expected
            assert result["annotation"] is None
            assert result["status"] == "confirmed"
            assert result["challenge"]


def test_uncertain_code_does_not_let_model_create_a_false_positive():
    model = StubModel()
    with TestClient(create_workbench(model=model)) as client:
        client.post("/api/session")
        result = diagnose(client, "def ok(xs):\n    return sum(xs)\n")
        assert result["status"] == "uncertain"
        assert not model.messages
        assert result["challenge"] is None
