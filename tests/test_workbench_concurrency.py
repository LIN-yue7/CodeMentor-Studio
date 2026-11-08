
from concurrent.futures import ThreadPoolExecutor
from uuid import uuid4

from fastapi.testclient import TestClient

from app.workbench import create_workbench
from tests.test_workbench_flow import CODE


def test_concurrent_retries_create_one_diagnosis_and_one_attempt():
    with TestClient(create_workbench()) as client:
        client.post("/api/session")
        payload = {"code": CODE, "request_id": str(uuid4()), "goal": "sum-all"}
        with ThreadPoolExecutor(max_workers=4) as pool:
            diagnoses = list(pool.map(lambda _: client.post("/api/diagnoses", json=payload), range(4)))
            assert all(response.status_code == 200 for response in diagnoses)
            assert len({response.json()["challenge"]["id"] for response in diagnoses}) == 1
            challenge_id = diagnoses[0].json()["challenge"]["id"]
            answer = {"answer": "5", "attempt_id": str(uuid4())}
            path = f"/api/challenges/{challenge_id}/answer"
            attempts = list(pool.map(lambda _: client.post(path, json=answer), range(4)))
            assert all(response.status_code == 200 for response in attempts)
            assert all(response.json() == attempts[0].json() for response in attempts)
        skill = client.get("/api/profile").json()["skills"][0]
        assert skill["diagnoses"] == 1
        assert skill["independent"] == 1


def test_tampered_cookie_cannot_read_profile():
    with TestClient(create_workbench()) as client:
        client.post("/api/session")
        name = "cm_session"
        cookie = client.cookies.get(name)
        client.cookies.clear()
        client.cookies.set(name, ("0" if cookie[0] != "0" else "1") + cookie[1:])
        assert client.get("/api/profile", headers={"X-Student-Id": "local"}).status_code == 401
