
from fastapi.testclient import TestClient

from app.workbench import create_workbench


def test_workbench_does_not_mount_local_admin_routes():
    with TestClient(create_workbench()) as client:
        assert client.get("/api/health").json() == {"status": "ok"}
        for path in ("/ui/index.html", "/api/v1/library", "/api/v1/report",
                     "/api/v1/tutor/errors", "/api/v1/auth/session", "/docs"):
            assert client.get(path).status_code == 404
        assert client.post("/api/analyze", json={}).status_code == 404


def test_workbench_rejects_cross_origin_mutation_and_large_payload():
    with TestClient(create_workbench()) as client:
        assert client.post("/api/session", headers={"Origin": "https://elsewhere.test"}).status_code == 403
        assert client.post("/api/session", content=b"x" * 100_000).status_code == 413
        response = client.post("/api/session")
        assert response.status_code == 200
        assert "httponly" in response.headers["set-cookie"].lower()
        assert "samesite=strict" in response.headers["set-cookie"].lower()
        assert "owner" not in response.json()
