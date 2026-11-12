import io
import stat
import zipfile

import pytest
from fortran_analyser.archive import extract_sources


def bundle(entries):
    output = io.BytesIO()
    with zipfile.ZipFile(output, "w", zipfile.ZIP_DEFLATED) as archive:
        for name, content in entries:
            archive.writestr(name, content)
    return output.getvalue()


def test_extracts_only_fortran_without_executing_project_files(tmp_path):
    data = bundle(
        [
            ("project/src/p.F90", "program p\nend\n"),
            ("project/build.sh", "exit 1"),
            ("project/reference/old.f90", "not fortran"),
        ]
    )
    assert extract_sources(data, tmp_path) == 1
    assert (tmp_path / "project/src/p.F90").read_text() == "program p\nend\n"
    assert not (tmp_path / "project/build.sh").exists()
    assert not (tmp_path / "project/reference").exists()


@pytest.mark.parametrize(
    "path",
    [
        "../escape.f90",
        "/absolute.f90",
        "C:/drive.f90",
        "a\\escape.f90",
        "a/../b.f90",
        "a//b.f90",
        "a/./b.f90",
        "CON.f90",
        "a./p.f90",
        "a /p.f90",
        "a:file.f90",
    ],
)
def test_rejects_unsafe_or_platform_ambiguous_paths(tmp_path, path):
    # ZipInfo normalizes native separators when writing on Windows. Restore
    # the raw ZIP filename to exercise incoming archives made on other systems.
    data = bundle([(path.replace("\\", "_"), "program p\nend\n")])
    if "\\" in path:
        data = data.replace(path.replace("\\", "_").encode(), path.encode())
    with pytest.raises(ValueError, match="ruta"):
        extract_sources(data, tmp_path)
    assert not list(tmp_path.iterdir())


def test_rejects_symlinks(tmp_path):
    info = zipfile.ZipInfo("link.f90")
    info.create_system = 3
    info.external_attr = (stat.S_IFLNK | 0o777) << 16
    with pytest.raises(ValueError, match="enlaces"):
        extract_sources(bundle([(info, "../elsewhere")]), tmp_path)


def test_rejects_duplicate_case_insensitive_paths(tmp_path):
    with pytest.raises(ValueError, match="duplicadas"):
        extract_sources(bundle([("P.f90", ""), ("p.f90", "")]), tmp_path)


def test_accepts_source_above_previous_two_mb_limit(tmp_path):
    assert extract_sources(bundle([("large.f90", " " * 2_000_001)]), tmp_path) == 1
    assert (tmp_path / "large.f90").stat().st_size == 2_000_001


def test_accepts_more_than_one_hundred_fortran_sources(tmp_path):
    assert extract_sources(bundle([(f"p{i}.f90", "") for i in range(151)]), tmp_path) == 151
    assert len(list(tmp_path.glob("*.f90"))) == 151


@pytest.mark.parametrize("data", [b"not a zip", bundle([("readme.txt", "text")])])
def test_invalid_or_empty_source_archive(tmp_path, data):
    with pytest.raises(ValueError):
        extract_sources(data, tmp_path)


def test_accepts_total_sources_above_previous_twenty_mb_limit(tmp_path):
    data = bundle([(f"p{i}.f90", b" " * 2_000_001) for i in range(11)])
    assert extract_sources(data, tmp_path) == 11
    assert sum(p.stat().st_size for p in tmp_path.glob("*.f90")) > 20_000_000


@pytest.mark.parametrize("format", ["zip", "tar", "7z"])
def test_accepts_more_than_one_thousand_entries(tmp_path, format):
    import tarfile

    import py7zr

    entries = [(f"dir/file{i}.txt", "") for i in range(1100)]
    entries.append(("p.f90", "program p\nend\n"))
    if format == "zip":
        data = bundle(entries)
    else:
        buffer = io.BytesIO()
        if format == "tar":
            with tarfile.open(fileobj=buffer, mode="w") as archive:
                for name, content in entries:
                    member = tarfile.TarInfo(name)
                    member.size = len(content)
                    archive.addfile(member, io.BytesIO(content.encode()))
        else:
            with py7zr.SevenZipFile(buffer, "w") as archive:
                for name, content in entries:
                    archive.writestr(content, name)
        data = buffer.getvalue()
    assert extract_sources(data, tmp_path) == 1
    assert (tmp_path / "p.f90").read_text() == "program p\nend\n"
    assert not (tmp_path / "dir").exists()


def test_paths_after_one_thousand_entries_are_still_validated(tmp_path):
    entries = [(f"file{i}.txt", "") for i in range(1100)]
    entries.append(("../escape.f90", "program p\nend"))
    with pytest.raises(ValueError, match="ruta"):
        extract_sources(bundle(entries), tmp_path)


def test_non_materialized_documentation_paths_need_not_be_windows_portable(tmp_path):
    data = bundle(
        [
            ("docs/About../", ""),
            ("docs/About../README", "documentation"),
            ("p.f90", "program p\nend"),
        ]
    )
    assert extract_sources(data, tmp_path) == 1
    assert not (tmp_path / "docs").exists()


def test_source_paths_still_require_portable_components(tmp_path):
    with pytest.raises(ValueError, match="ruta"):
        extract_sources(bundle([("About../p.f90", "program p\nend")]), tmp_path)
