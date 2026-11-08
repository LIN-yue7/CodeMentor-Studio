
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


def diagnose(client, code=CODE, request_id=None):
    response = client.post("/api/diagnoses", json={"code": code, "request_id": request_id or key()})
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
        assert stranger.post(f"{path}/hint").status_code == 404
        assert student.post(f"{path}/hint").json()["used"] == 1
        attempt_id = key()
        payload = {"answer": "5", "attempt_id": attempt_id}
        result = student.post(f"{path}/answer", json=payload)
        assert result.status_code == 200, result.text
        assert result.json()["outcome"] == "assisted"
        assert result.json()["recommendation"] == "repeat"
        assert student.post(f"{path}/answer", json=payload).json() == result.json()
        assert student.post(f"{path}/answer", json={**payload, "answer": "999"}).status_code == 409
        assert student.post(f"{path}/hint").status_code == 409
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
            result = diagnose(client, code)
            item = result["evidence"][0]
            assert item["knowledge_id"] == concept
            assert item["observed"] != item["expected"]
