import json
import uuid

from fastapi.testclient import TestClient
from fortran_analyser.api import create_app
from fortran_analyser.jobs import Job, JobStore
from test_api import upload, wait
from test_archive import bundle


def test_results_and_sources_survive_restart_and_delete_is_durable(tmp_path, monkeypatch):
    monkeypatch.setenv("FORTRAN_DATA_DIR", str(tmp_path))
    with TestClient(create_app()) as client:
        assert client.get("/api/config").json() == {"persistent": True}
        response = upload(client, bundle([("src/p.f90", "program p\nimplicit none\nend\n")]))
        identifier = response.json()["id"]
        assert wait(client, identifier)["status"] == "completed"
        original = client.get(f"/api/analyses/{identifier}/report").json()
    with TestClient(create_app()) as client:
        assert client.get(f"/api/analyses/{identifier}").json()["status"] == "completed"
        assert client.get(f"/api/analyses/{identifier}/report").json() == original
        assert client.get("/api/analyses").json()[0]["id"] == identifier
        source = client.get(f"/api/analyses/{identifier}/source", params={"path": "src/p.f90"})
        assert source.json()["content"] == "program p\nimplicit none\nend\n"
        assert client.delete(f"/api/analyses/{identifier}").status_code == 200
    with TestClient(create_app()) as client:
        assert client.get(f"/api/analyses/{identifier}").status_code == 404
    assert not (tmp_path / "analyses" / identifier).exists()


def test_failed_uploads_do_not_leave_sources_on_disk(tmp_path, monkeypatch):
    monkeypatch.setenv("FORTRAN_DATA_DIR", str(tmp_path))
    with TestClient(create_app()) as client:
        identifier = upload(client, bundle([("p.f90", ""), ("../bad", "")])).json()["id"]
        assert wait(client, identifier)["status"] == "failed"
    directory = tmp_path / "analyses" / identifier
    assert [p.name for p in directory.iterdir()] == [".analysis.json"]
    with TestClient(create_app()) as client:
        assert client.get(f"/api/analyses/{identifier}").json()["status"] == "failed"


def test_interrupted_work_is_reported_not_silently_restarted(tmp_path):
    identifier = uuid.uuid4().hex
    directory = tmp_path / identifier
    directory.mkdir()
    job = Job(identifier, "Interrupted", "auto", status="running", total=1)
    (directory / ".analysis.json").write_text(
        json.dumps(
            {
                "storage_version": 1,
                "job": job.snapshot(),
                "report": None,
            }
        )
    )
    (directory / "unfinished.f90").write_text("program unfinished")
    store = JobStore(tmp_path, persistent=True)
    try:
        recovered = store.get(identifier)
        assert recovered.status == "failed"
        assert "reinicio" in recovered.error
        assert not (directory / "unfinished.f90").exists()
        assert (directory / ".analysis.json").exists()
    finally:
        store.close()


def test_corrupt_and_unrelated_files_are_preserved(tmp_path):
    (tmp_path / "unrelated.txt").write_text("preserve this")
    directory = tmp_path / uuid.uuid4().hex
    directory.mkdir()
    state = directory / ".analysis.json"
    state.write_text("not valid json")
    store = JobStore(tmp_path, persistent=True)
    try:
        assert not store.jobs
        assert state.read_text() == "not valid json"
        assert (tmp_path / "unrelated.txt").read_text() == "preserve this"
    finally:
        store.close()


def test_configurable_nas_hostname_still_rejects_unknown_hosts(monkeypatch):
    monkeypatch.setenv("FORTRAN_ALLOWED_HOSTS", "truenas.local,192.168.1.20")
    with TestClient(create_app()) as client:
        assert client.get("/api/health", headers={"Host": "truenas.local:8890"}).status_code == 200
        assert client.get("/api/health", headers={"Host": "192.168.1.20:8890"}).status_code == 200
        assert client.get("/api/health", headers={"Host": "unknown.example"}).status_code == 400
