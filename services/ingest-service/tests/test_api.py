import os
from pathlib import Path
from unittest.mock import patch

os.environ["DATA_DIR"] = str(Path(__file__).parent / ".test-data")
os.environ["MOCK_AUTH"] = "true"
os.environ["APP_ENV"] = "local"

from fastapi.testclient import TestClient
from fastapi import HTTPException
from app.main import app
from app.auth import get_principal
from app.config import Settings

client = TestClient(app)


def test_health_and_version():
    assert client.get("/health").json() == {"status": "ok"}
    assert client.get("/version").status_code == 200


def test_job_lifecycle_starts():
    audio = b"fake-audio"
    response = client.post("/api/jobs", json={"filename": "meeting.mp3", "content_type": "audio/mpeg", "size_bytes": len(audio), "language": "auto", "generate_video": False})
    assert response.status_code == 201
    job_id = response.json()["job"]["id"]
    assert client.put(f"/api/uploads/{job_id}", content=audio).status_code == 204
    assert client.post(f"/api/jobs/{job_id}/start").status_code == 200


def test_rejects_unsupported_type():
    response = client.post("/api/jobs", json={"filename": "notes.txt", "content_type": "text/plain", "size_bytes": 5})
    assert response.status_code == 422


def test_mock_auth_is_rejected_outside_local_mode():
    try:
        get_principal(settings=Settings(mock_auth=True, app_env="production"))
    except HTTPException as exc:
        assert exc.status_code == 503
    else:
        raise AssertionError("mock authentication must not be accepted outside local mode")


def test_mock_auth_fails_closed_when_app_env_is_unset():
    with patch.dict(os.environ, {}, clear=True):
        settings = Settings(mock_auth=True, _env_file=None)
    assert settings.app_env == "production"
    try:
        get_principal(settings=settings)
    except HTTPException as exc:
        assert exc.status_code == 503
    else:
        raise AssertionError("mock authentication must be disabled by the default environment")

