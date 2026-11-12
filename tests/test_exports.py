import bz2
import gzip
import io
import lzma
import tarfile

import py7zr
import pytest
from fastapi.testclient import TestClient
from fortran_analyser.api import create_app
from fortran_analyser.archive import extract_sources
from test_api import upload, wait


@pytest.mark.parametrize("compression", [None, gzip.compress, bz2.compress, lzma.compress])
def test_tar_formats(tmp_path, compression):
    buffer = io.BytesIO()
    with tarfile.open(fileobj=buffer, mode="w") as archive:
        item = tarfile.TarInfo("src/p.f90")
        content = b"program p\nimplicit none\nend\n"
        item.size = len(content)
        archive.addfile(item, io.BytesIO(content))
    data = buffer.getvalue()
    assert extract_sources(compression(data) if compression else data, tmp_path) == 1
    assert (tmp_path / "src/p.f90").read_bytes() == content


@pytest.mark.parametrize("compression", [gzip.compress, bz2.compress, lzma.compress])
def test_single_compressed_source(tmp_path, compression):
    assert extract_sources(compression(b"program p\nend"), tmp_path, "p.f90.gz") == 1


def test_7zip(tmp_path):
    buffer = io.BytesIO()
    with py7zr.SevenZipFile(buffer, "w") as archive:
        archive.writestr("program p\nend\n", "src/p.f90")
    assert extract_sources(buffer.getvalue(), tmp_path) == 1
    assert (tmp_path / "src/p.f90").exists()


@pytest.mark.parametrize(
    "name,kind",
    [
        ("../escape.f90", tarfile.REGTYPE),
        ("link.f90", tarfile.SYMTYPE),
        ("hard.f90", tarfile.LNKTYPE),
    ],
)
def test_tar_rejects_traversal_and_links(tmp_path, name, kind):
    buffer = io.BytesIO()
    with tarfile.open(fileobj=buffer, mode="w") as archive:
        item = tarfile.TarInfo(name)
        item.type = kind
        item.linkname = "../outside"
        archive.addfile(item)
    with pytest.raises(ValueError):
        extract_sources(buffer.getvalue(), tmp_path)


def test_compression_bomb(tmp_path):
    with pytest.raises(ValueError, match="20 MB"):
        extract_sources(gzip.compress(b" " * 20_000_001), tmp_path)


def test_pdf_api_has_report_signature_and_rejects_unknown_job():
    from pypdf import PdfReader

    with TestClient(create_app()) as client:
        assert client.get("/api/analyses/unknown/report.pdf").status_code == 404
        identifier = upload(client, client.get("/api/example").content).json()["id"]
        assert wait(client, identifier)["status"] == "completed"
        response = client.get(f"/api/analyses/{identifier}/report.pdf")
        assert response.status_code == 200
        assert response.headers["content-type"] == "application/pdf"
        assert "attachment" in response.headers["content-disposition"]
        reader = PdfReader(io.BytesIO(response.content))
        text = "".join(p.extract_text() for p in reader.pages)
        assert "SHA-256" in text and "Firma virtual" in text
        assert "FA102" in text  # example preprocessing limitation stays visible
        assert "CC parcial" in text
        assert "Diagrama" in text
