from pathlib import Path
from unittest.mock import patch

from fastapi.testclient import TestClient
from fortran_analyser.api import create_app
from test_api import wait
from test_archive import bundle


def start(client):
    response = client.post("/api/uploads?name=Test.tar.gz")
    assert response.status_code == 201
    return response.json()["id"]


def test_chunked_upload_reassembles_and_analyses():
    with TestClient(create_app()) as client:
        identifier = start(client)
        data = bundle([("p.f90", "program p\nend")])
        for offset in range(0, len(data), 50):
            chunk = data[offset : offset + 50]
            response = client.put(f"/api/uploads/{identifier}?offset={offset}", content=chunk)
            assert response.json() == {"received": offset + len(chunk)}
        response = client.post(f"/api/uploads/{identifier}/complete?size={len(data)}")
        assert response.status_code == 202
        assert wait(client, identifier)["status"] == "completed"
        assert not list(client.app.state.store.root.glob("*.upload"))
        assert client.post(f"/api/uploads/{identifier}/complete?size=1").status_code == 409


def test_cancel_order_and_incomplete_finalize():
    with TestClient(create_app()) as client:
        identifier = start(client)
        url = f"/api/uploads/{identifier}"
        assert client.put(url + "?offset=0", content=b"test").status_code == 200
        assert client.put(url + "?offset=0", content=b"repeat").status_code == 409
        assert client.put(url + "?offset=4", content=b"x" * 13).status_code == 200
        assert client.put(url + "?offset=17", content=b"x" * (8 * 1024**2 + 1)).status_code == 200
        assert client.post(url + "/complete?size=5").status_code == 409
        assert client.delete(f"/api/analyses/{identifier}").json()["deleted"]
        assert client.put(url + "?offset=4", content=b"x").status_code == 404
        assert not list(client.app.state.store.root.glob("*.upload"))
        assert not client.app.state.store.jobs


def test_upload_is_retained_without_automatic_deadline():
    with TestClient(create_app()) as client:
        identifier = start(client)
        client.app.state.store.jobs[identifier].last_activity -= 1801
        assert client.get("/api/analyses").json()[0]["id"] == identifier
        assert client.delete(f"/api/analyses/{identifier}").status_code == 200
        assert not list(client.app.state.store.root.glob("*.upload"))


def test_proxy_sized_requests_accept_a_larger_total():
    data = b"x" * (24 * 1024**2 + 7)

    def verify(path, destination, filename, should_cancel=None):
        assert isinstance(path, Path)
        assert path.read_bytes() == data
        raise ValueError("Reception verified")

    with patch("fortran_analyser.jobs.bounded_extract", side_effect=verify):
        with TestClient(create_app()) as client:
            identifier = start(client)
            for offset in range(0, len(data), 8 * 1024**2):
                chunk = data[offset : offset + 8 * 1024**2]
                assert (
                    client.put(
                        f"/api/uploads/{identifier}?offset={offset}", content=chunk
                    ).status_code
                    == 200
                )
            assert (
                client.post(f"/api/uploads/{identifier}/complete?size={len(data)}").status_code
                == 202
            )
            assert wait(client, identifier)["error"] == "Reception verified"
