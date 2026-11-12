"""Large-upload contracts tested with chunks and scaled limits, never giant RAM buffers."""

import os
from pathlib import Path
from unittest.mock import patch

import pytest
from fastapi.testclient import TestClient
from fortran_analyser.api import create_app
from fortran_analyser.archive import extract_sources
from fortran_analyser.jobs import JobStore
from test_api import wait
from test_archive import bundle


def test_no_upload_maximum_is_reported():
    with TestClient(create_app()) as client:
        assert client.get("/api/config").json()["max_upload_bytes"] is None


@pytest.mark.parametrize("length", [32, 33])
def test_streamed_upload_without_content_length_has_no_quota(length):
    with TestClient(create_app()) as client:
        response = client.post(
            "/api/analyses",
            content=iter([b"x" * length]),
            headers={"Content-Type": "application/octet-stream"},
        )
        assert response.status_code == 202
        assert wait(client, response.json()["id"])["status"] == "failed"
        assert not list(client.app.state.store.root.glob("*.upload"))


def test_large_upload_is_queued_as_disk_path_and_cleaned():
    seen = []

    def inspect_upload(data, destination, filename, should_cancel=None):
        assert isinstance(data, Path)
        assert data.stat().st_size == 32 * 1024**2
        seen.append(data)
        raise ValueError("test extraction")

    with patch("fortran_analyser.jobs.bounded_extract", side_effect=inspect_upload):
        with TestClient(create_app()) as client:
            response = client.post(
                "/api/analyses",
                content=(b"x" * 1024**2 for _ in range(32)),
                headers={"Content-Type": "application/octet-stream"},
            )
            assert response.status_code == 202
            assert wait(client, response.json()["id"])["status"] == "failed"
            assert seen and not seen[0].exists()


def test_file_archive_input_and_archive_cleanup_on_success():
    with TestClient(create_app()) as client:
        response = client.post(
            "/api/analyses",
            content=bundle([("p.f90", "program p\nend")]),
            headers={"Content-Type": "application/octet-stream"},
        )
        assert wait(client, response.json()["id"])["status"] == "completed"
        assert not list(client.app.state.store.root.glob("*.upload"))


def test_restart_removes_owned_abandoned_upload_only(tmp_path):
    abandoned = tmp_path / ("a" * 32 + ".upload")
    abandoned.write_bytes(b"partial")
    unrelated = tmp_path / "unrelated.upload"
    unrelated.write_bytes(b"preserve")
    store = JobStore(tmp_path, persistent=True)
    store.close()
    assert not abandoned.exists()
    assert unrelated.read_bytes() == b"preserve"


@pytest.mark.skipif(os.name == "nt", reason="Sparse 4-GiB fixture uses Linux filesystem holes")
def test_real_four_gib_archive_on_disk(tmp_path):
    payload = bundle([("p.f90", "program p\nend")])
    archive = tmp_path / "large.zip"
    with archive.open("wb") as stream:
        stream.seek(4 * 1024**3 + 1 - len(payload))
        stream.write(payload)
    destination = tmp_path / "sources"
    destination.mkdir()
    assert archive.stat().st_size == 4 * 1024**3 + 1
    assert extract_sources(archive, destination) == 1
    archive.unlink()
