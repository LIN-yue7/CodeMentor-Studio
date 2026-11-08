
from uuid import uuid4

from fastapi.testclient import TestClient

from app.workbench import create_workbench


CODE = """def total(xs):
    result = 0
    for i in range(len(xs) - 1):
        result += xs[i]
    return result
"""


def key():
    return str(uuid4())


def diagnose(client, code=CODE, request_id=None, goal="sum-all"):
    response = client.post("/api/diagnoses", json={"code": code, "request_id": request_id or key(), "goal": goal})
    assert response.status_code == 200, response.text
    return response.json()


def test_diagnosis_attempt_and_retest_are_persistent_and_isolated():
    app = create_workbench()
    with TestClient(app) as student, TestClient(app) as stranger:
        assert student.get("/api/profile").status_code == 401
        student.post("/api/session")
        stranger.post("/api/session")
        request_id = key()
        diagnosis = diagnose(student, request_id=request_id)
        assert diagnose(student, request_id=request_id) == diagnosis
        assert student.post("/api/diagnoses", json={"code": CODE + "# changed", "request_id": request_id}).status_code == 409
        assert diagnosis["evidence"][0]["line"] == 3
        assert diagnosis["evidence"][0]["knowledge_id"] == "loop-boundary"
        challenge = diagnosis["challenge"]
        assert "answer" not in challenge and "hints" not in challenge
        challenge_id = challenge["id"]
        path = f"/api/challenges/{challenge_id}"
        assert stranger.post(f"{path}/hint", json={"tier": 1}).status_code == 404
        assert student.post(f"{path}/hint", json={"tier": 1}).json()["used"] == 1
        attempt_id = key()
        payload = {"answer": "6", "attempt_id": attempt_id}
        result = student.post(f"{path}/answer", json=payload)
        assert result.status_code == 200, result.text
        assert result.json()["outcome"] == "assisted"
        assert result.json()["recommendation"] == "repeat"
        assert student.post(f"{path}/answer", json=payload).json() == result.json()
        assert student.post(f"{path}/answer", json={**payload, "answer": "999"}).status_code == 409
        assert student.post(f"{path}/hint", json={"tier": 1}).status_code == 409
        retry = student.post(f"{path}/retry").json()
        assert retry["template_id"] != challenge["template_id"]
        assert student.post(f"{path}/retry").json() == retry
        independent = student.post(f"/api/challenges/{retry['id']}/answer",
                                   json={"answer": "7", "attempt_id": key()}).json()
        assert independent["outcome"] == "independent"
        assert independent["recommendation"] == "transfer"
        assert student.get("/api/profile").json()["skills"][0]["independent"] == 1
        assert stranger.get("/api/profile").json()["skills"] == []


def test_unrecognized_or_syntax_error_is_not_recorded_as_concept_error():
    with TestClient(create_workbench()) as client:
        client.post("/api/session")
        result = diagnose(client, "import os\nos.system('exit 1')")
        assert result["status"] == "uncertain"
        assert result["challenge"] is None
        result = diagnose(client, "def broken(:")
        assert result["status"] == "syntax-error"
        assert client.get("/api/profile").json()["skills"] == []


def test_supported_concepts_have_concrete_counterexamples():
    with TestClient(create_workbench()) as client:
        client.post("/api/session")
        for code, concept in (
            ("def first(xs):\n    return xs[0]\n", "empty-list"),
            ("def total(xs):\n    for x in xs:\n        result = 0\n        result += x\n    return result\n", "accumulator"),
        ):
            result = diagnose(client, code, goal="first-or-empty" if concept == "empty-list" else "sum-all")
            item = result["evidence"][0]
            assert item["knowledge_id"] == concept
            assert item["observed"] != item["expected"]

def test_semantic_diagnosis_requires_matching_task_contract():
    with TestClient(create_workbench()) as client:
        client.post("/api/session")
        for goal in (None, "first-or-empty"):
            response = client.post("/api/diagnoses", json={
                "code": CODE, "request_id": key(), "goal": goal,
            })
            assert response.status_code == 200, response.text
            assert response.json()["status"] == "uncertain"
        assert client.get("/api/profile").json()["skills"] == []

def test_no_exercise_matches_visible_answer_or_counts_revealed_template_as_independent():
    with TestClient(create_workbench()) as client:
        client.post("/api/session")
        initial = diagnose(client)
        challenge = initial["challenge"]
        assert initial["evidence"][0]["counterexample"] not in challenge["prompt"]
        path = f"/api/challenges/{challenge['id']}"
        for _ in range(2):
            result = client.post(f"{path}/hint", json={"tier": 1})
            assert result.status_code == 200, result.text
            assert result.json()["used"] == 1
        assert client.post(f"{path}/answer", json={"answer": "6", "attempt_id": key()}).json()["outcome"] == "assisted"
        for expected in ("boundary-b-v1", "boundary-c-v1"):
            next_challenge = diagnose(client)["challenge"]
            assert next_challenge["template_id"] == expected
            client.post(f"/api/challenges/{next_challenge['id']}/answer", json={"answer": "0", "attempt_id": key()})
        repeat = diagnose(client)["challenge"]
        assert client.post(f"/api/challenges/{repeat['id']}/answer",
                           json={"answer": "6", "attempt_id": key()}).json()["outcome"] == "assisted"
