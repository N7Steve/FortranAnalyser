import threading
import time
from unittest.mock import patch

import pytest
from fastapi.testclient import TestClient
from fortran_analyser.api import create_app
from test_archive import bundle


@pytest.fixture
def client():
    with TestClient(create_app()) as client:
        yield client


def upload(client, data, name="Example"):
    return client.post(
        "/api/analyses",
        params={"name": name},
        content=data,
        headers={"Content-Type": "application/zip"},
    )


def wait(client, identifier):
    deadline = time.monotonic() + 15
    while time.monotonic() < deadline:
        job = client.get(f"/api/analyses/{identifier}").json()
        if job["status"] in {"completed", "failed", "cancelled"}:
            return job
        time.sleep(0.02)
    pytest.fail("Job did not finish within 15 seconds")


def test_full_example_flow_report_source_download_and_delete(client):
    sample = client.get("/api/example")
    assert sample.status_code == 200
    response = upload(client, sample.content)
    assert response.status_code == 202
    identifier = response.json()["id"]
    job = wait(client, identifier)
    assert job["status"] == "completed", job
    report = client.get(f"/api/analyses/{identifier}/report").json()
    assert report["summary"]["files"] == 3
    assert report["summary"]["ok"] == 2
    assert report["summary"]["partial"] == 1
    assert {f["rule"] for file in report["files"] for f in file["findings"]} >= {
        "FA001",
        "FA002",
        "FA102",
    }
    source = client.get(f"/api/analyses/{identifier}/source", params={"path": "example/model.f90"})
    assert source.status_code == 200
    assert "module transport_model" in source.json()["content"]
    download = client.get(f"/api/analyses/{identifier}/report?download=true")
    assert "attachment" in download.headers["content-disposition"]
    assert download.json() == report
    assert (
        client.get(f"/api/analyses/{identifier}/source", params={"path": "../secret"}).status_code
        == 404
    )
    assert client.delete(f"/api/analyses/{identifier}").json() == {"deleted": True}
    assert client.get(f"/api/analyses/{identifier}").status_code == 404


def test_bad_zip_becomes_visible_failure_and_cleans_files(client):
    identifier = upload(
        client, bundle([("valid.f90", "program p\nend\n"), ("../p.f90", "")])
    ).json()["id"]
    job = wait(client, identifier)
    assert job["status"] == "failed"
    assert "ruta" in job["error"]
    assert not (client.app.state.store.root / identifier).exists()
    assert client.get(f"/api/analyses/{identifier}/report").status_code == 409


def test_upload_limit_and_media_type_release_reserved_slot(client):
    assert client.post("/api/analyses", content="text").status_code == 415
    for _ in range(4):
        assert upload(client, b"x" * 10_000_001).status_code == 413
    assert not client.app.state.store.jobs


def test_api_remains_responsive_and_queue_is_bounded(client):
    entered = threading.Event()
    release = threading.Event()

    def blocked(*args, **kwargs):
        entered.set()
        release.wait(timeout=5)
        raise ValueError("Stopped for queue test")

    with patch("fortran_analyser.jobs.analyse_project", side_effect=blocked):
        data = bundle([("p.f90", "program p\nend\n")])
        first = upload(client, data).json()["id"]
        assert entered.wait(timeout=2)
        try:
            assert client.get("/api/health").json() == {"status": "ok"}
            assert client.get(f"/api/analyses/{first}").json()["status"] == "running"
            assert upload(client, data).status_code == 202
            assert upload(client, data).status_code == 202
            assert upload(client, data).status_code == 429
            assert client.delete(f"/api/analyses/{first}").status_code == 202
        finally:
            release.set()
        assert wait(client, first)["status"] == "cancelled"


def test_invalid_source_still_completes_report_and_source_encoding_is_explicit(client):
    data = bundle([("broken.f90", b"\xff")])
    identifier = upload(client, data).json()["id"]
    assert wait(client, identifier)["status"] == "completed"
    report = client.get(f"/api/analyses/{identifier}/report").json()
    assert report["summary"]["failed"] == 1
    assert (
        client.get(f"/api/analyses/{identifier}/source", params={"path": "broken.f90"}).status_code
        == 422
    )


def test_unknown_job_and_unknown_host_are_rejected(client):
    assert client.get("/api/analyses/unknown").status_code == 404
    assert client.get("/api/health", headers={"Host": "untrusted.example"}).status_code == 400


def test_cors_allows_only_local_development_origin(client):
    headers = {
        "Origin": "http://127.0.0.1:5173",
        "Access-Control-Request-Method": "POST",
        "Access-Control-Request-Headers": "content-type",
    }
    assert client.options("/api/analyses", headers=headers).status_code == 200
    headers["Origin"] = "https://untrusted.example"
    assert client.options("/api/analyses", headers=headers).status_code == 400


def test_configured_frontend_is_served_without_exposing_sources(tmp_path, monkeypatch):
    (tmp_path / "index.html").write_text("<h1>Compiled application</h1>")
    monkeypatch.setenv("FORTRAN_FRONTEND_DIR", str(tmp_path))
    with TestClient(create_app()) as web:
        assert web.get("/").text == "<h1>Compiled application</h1>"
        assert web.get("/api/health").json() == {"status": "ok"}
        assert web.get("/reference/pom.xml").status_code == 404
