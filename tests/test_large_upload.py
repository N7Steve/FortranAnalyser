"""Large-upload contracts tested with chunks and scaled limits, never giant RAM buffers."""

import os
from pathlib import Path
from unittest.mock import patch

import pytest
from fastapi.testclient import TestClient
from fortran_analyser.api import create_app
from fortran_analyser.archive import MAX_UPLOAD, extract_sources
from fortran_analyser.jobs import JobStore
from test_api import wait
from test_archive import bundle


def test_limit_is_four_gib_and_excess_length_is_rejected_without_reserving_slot():
    assert MAX_UPLOAD == 4 * 1024**3
    with TestClient(create_app()) as client:
        response = client.post(
            "/api/analyses",
            content=b"",
            headers={
                "Content-Type": "application/octet-stream",
                "Content-Length": str(MAX_UPLOAD + 1),
            },
        )
        assert response.status_code == 413
        assert not client.app.state.store.jobs
        assert not list(client.app.state.store.root.glob("*.upload"))


@pytest.mark.parametrize("extra,expected", [(0, 202), (1, 413)])
def test_chunked_boundary_without_content_length(monkeypatch, extra, expected):
    monkeypatch.setattr("fortran_analyser.api.MAX_UPLOAD", 32)
    with TestClient(create_app()) as client:
        response = client.post(
            "/api/analyses",
            content=iter([b"x" * 16, b"x" * (16 + extra)]),
            headers={"Content-Type": "application/octet-stream"},
        )
        assert response.status_code == expected
        if expected == 202:
            assert wait(client, response.json()["id"])["status"] == "failed"
        else:
            assert not client.app.state.store.jobs
        assert not list(client.app.state.store.root.glob("*.upload"))


def test_large_upload_is_queued_as_disk_path_and_cleaned():
    seen = []

    def inspect_upload(data, destination, filename):
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
        stream.seek(MAX_UPLOAD - len(payload))
        stream.write(payload)
    destination = tmp_path / "sources"
    destination.mkdir()
    assert archive.stat().st_size == MAX_UPLOAD
    assert extract_sources(archive, destination) == 1
    with archive.open("ab") as stream:
        stream.write(b"x")
    with pytest.raises(ValueError, match="4 GiB"):
        extract_sources(archive, destination)
    archive.unlink()
