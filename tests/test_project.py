import json
import subprocess
import sys
from pathlib import Path

import pytest
from fortran_analyser import analyse_project

FIXTURES = Path(__file__).parent / "fixtures" / "project"


def test_project_fixture_has_expected_status_and_paths():
    report = analyse_project(FIXTURES)
    assert report.summary == {
        "ok": 2,
        "partial": 0,
        "failed": 0,
        "skipped": 0,
        "files": 2,
        "findings": 1,
    }
    assert [f.path for f in report.files] == ["legacy.f", "modern.f90"]
    assert report.to_dict()["files"][0]["metrics"]["declared_entities"] == 3


def test_mixed_project_keeps_valid_files_and_ignores_reference(tmp_path):
    (tmp_path / "ok.F90").write_text("program p\nimplicit none\nend\n")
    (tmp_path / "bad.f90").write_text("not fortran\n")
    (tmp_path / "macro.f90").write_text("#define N 3\nprogram p\nend\n")
    (tmp_path / "reference").mkdir()
    (tmp_path / "reference" / "ignored.f90").write_text("not fortran")
    report = analyse_project(tmp_path)
    assert report.summary["files"] == 3
    assert report.summary["ok"] == 1
    assert report.summary["partial"] == 1
    assert report.summary["failed"] == 1


def test_size_and_encoding_failures_are_visible(tmp_path):
    (tmp_path / "large.f90").write_bytes(b"a" * 100)
    (tmp_path / "encoding.f90").write_bytes(b"\xff")
    report = analyse_project(tmp_path, max_file_bytes=50)
    assert report.summary["skipped"] == 1
    assert report.summary["failed"] == 1
    assert all(f.metrics is None for f in report.files)


def test_timeout_terminates_worker(tmp_path):
    (tmp_path / "p.f90").write_text("program p\nend\n")
    report = analyse_project(tmp_path, timeout=0.000001)
    assert report.files[0].status == "failed"
    assert report.files[0].findings[0].rule == "FA105"


def test_file_count_limit_does_not_silently_truncate():
    with pytest.raises(ValueError, match="límite"):
        analyse_project(FIXTURES, max_files=1)


@pytest.mark.parametrize("path", ["missing", "empty", "wrong.txt"])
def test_invalid_input_is_configuration_error(tmp_path, path):
    (tmp_path / "empty").mkdir()
    (tmp_path / "wrong.txt").write_text("program p\nend\n")
    with pytest.raises(ValueError):
        analyse_project(tmp_path / path)


def test_form_override(tmp_path):
    source = tmp_path / "free.f"
    source.write_text("program p\nimplicit none\nend\n")
    report = analyse_project(source, source_form="free")
    assert report.files[0].status == "ok"


def test_symbolic_file_is_not_followed(tmp_path):
    original = tmp_path / "original.txt"
    original.write_text("program p\nend\n")
    nested = tmp_path / "nested"
    nested.mkdir()
    try:
        (nested / "link.f90").symlink_to(original)
    except OSError:
        pytest.skip("This environment does not permit creating symbolic links")
    report = analyse_project(nested)
    assert report.files[0].status == "skipped"


def test_cli_json_output_and_exit_codes(tmp_path):
    output = tmp_path / "report.json"
    run = subprocess.run(
        [sys.executable, "-m", "fortran_analyser", str(FIXTURES), "-o", str(output)],
        capture_output=True,
        text=True,
        timeout=30,
    )
    assert run.returncode == 0, run.stderr
    assert not run.stdout
    assert json.loads(output.read_text(encoding="utf-8"))["summary"]["ok"] == 2
    invalid = tmp_path / "bad.f90"
    invalid.write_text("not fortran")
    run = subprocess.run(
        [sys.executable, "-m", "fortran_analyser", str(invalid)],
        capture_output=True,
        text=True,
        timeout=30,
    )
    assert run.returncode == 1
    assert json.loads(run.stdout)["files"][0]["status"] == "failed"
    run = subprocess.run(
        [sys.executable, "-m", "fortran_analyser", str(tmp_path / "missing")],
        capture_output=True,
        text=True,
        timeout=30,
    )
    assert run.returncode == 2
    assert not run.stdout
    assert "Error:" in run.stderr


def test_api_requires_finite_positive_limits():
    for limit in (0, -1, float("nan"), float("inf")):
        with pytest.raises(ValueError):
            analyse_project(FIXTURES, timeout=limit)


def test_cli_does_not_overwrite_input(tmp_path):
    path = tmp_path / "source.f90"
    original = "program p\nend\n"
    path.write_text(original)
    run = subprocess.run(
        [sys.executable, "-m", "fortran_analyser", str(path), "-o", str(path)],
        capture_output=True,
        text=True,
        timeout=30,
    )
    assert run.returncode == 2
    assert path.read_text() == original


def test_cli_directory_output_cannot_overwrite_an_analysed_file(tmp_path):
    path = tmp_path / "source.f90"
    original = "program p\nend\n"
    path.write_text(original)
    run = subprocess.run(
        [sys.executable, "-m", "fortran_analyser", str(tmp_path), "-o", str(path)],
        capture_output=True,
        text=True,
        timeout=30,
    )
    assert run.returncode == 2
    assert path.read_text() == original
