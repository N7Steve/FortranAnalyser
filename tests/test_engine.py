from pathlib import Path

import pytest
from fortran_analyser import analyse_source

FIXTURES = Path(__file__).parent / "fixtures" / "project"


def test_inline_comment_four_entities_and_shadow_are_not_keywords():
    result = analyse_source(
        "program p\nimplicit none ! valid comment\ninteger :: a,b,c,shadow\n"
        "shadow=1\nprint *, 'DO ! CALL INCLUDE'\nend\n"
    )
    assert result.status == "ok"
    assert result.metrics.declared_entities == 4
    assert result.metrics.loops == 0
    assert result.metrics.calls == 0
    assert result.scopes[0].implicit_none is True
    assert not result.findings


@pytest.mark.parametrize("kind", ["subroutine", "real function"])
def test_bare_end_closes_routine(kind):
    result = analyse_source(f"{kind} x()\nimplicit none\nend\n")
    assert result.status == "ok"
    assert len(result.scopes) == 1
    assert result.scopes[0].end_line == 3
    assert result.metrics.subroutines + result.metrics.functions == 1


def test_free_form_project_fixture():
    source = (FIXTURES / "modern.f90").read_text()
    result = analyse_source(source, path="modern.f90")
    assert result.status == "ok"
    metrics = result.metrics
    assert (metrics.modules, metrics.subroutines, metrics.functions) == (1, 1, 1)
    assert (metrics.declarations, metrics.declared_entities) == (6, 12)
    assert (metrics.loops, metrics.max_loop_depth, metrics.calls) == (2, 2, 1)
    assert all(scope.implicit_none for scope in result.scopes)
    assert not result.findings


def test_fixed_form_shared_terminal_loops():
    source = (FIXTURES / "legacy.f").read_text()
    result = analyse_source(source, source_form="fixed")
    assert result.status == "ok"
    assert result.metrics.subroutines == 1
    assert result.metrics.declared_entities == 3
    assert (result.metrics.loops, result.metrics.max_loop_depth) == (2, 2)
    assert [(f.rule, f.line) for f in result.findings] == [("FA001", 2)]


def test_scope_inheritance_and_explicit_override():
    result = analyse_source(
        "module m\nimplicit none\ncontains\nsubroutine child\nend\n"
        "subroutine override\nimplicit real(a-z)\nend\nend module\n"
        "subroutine external\nend\n"
    )
    assert result.status == "ok"
    assert [(s.qualified_name, s.implicit_none) for s in result.scopes] == [
        ("m", True),
        ("m::child", True),
        ("m::override", False),
        ("external", False),
    ]
    assert [(f.rule, f.line) for f in result.findings] == [("FA001", 6), ("FA001", 10)]


def test_child_none_does_not_cover_parent_and_interface_is_not_implementation():
    result = analyse_source(
        "module m\ninterface\nsubroutine signature(a)\ninteger :: a\n"
        "end subroutine\nend interface\ntype :: thing\ninteger :: field\nend type\n"
        "contains\nsubroutine child\nimplicit none\nend\nend module\n"
    )
    assert result.status == "ok"
    assert [(s.name, s.implicit_none) for s in result.scopes] == [("m", False), ("child", True)]
    assert result.metrics.subroutines == 1
    assert result.metrics.declared_entities == 0
    assert [(f.rule, f.line) for f in result.findings] == [("FA001", 1)]


def test_nested_loop_finding_has_location_and_no_performance_claim():
    result = analyse_source(
        "program p\nimplicit none\ninteger :: i,j,k,l\n"
        "do i=1,2\ndo j=1,2\ndo k=1,2\ndo l=1,2\n"
        "print *, i\nenddo\nenddo\nenddo\nenddo\nend\n",
        path="deep.f90",
    )
    assert result.metrics.max_loop_depth == 4
    assert [(f.rule, f.path, f.line, f.severity) for f in result.findings] == [
        ("FA002", "deep.f90", 7, "info"),
    ]


@pytest.mark.parametrize("source", ["", "\n! DO CALL INCLUDE\n"])
def test_empty_and_comment_only(source):
    result = analyse_source(source)
    assert result.status == "ok"
    assert result.metrics.physical_lines == len(source.splitlines())
    assert not result.scopes
    assert not result.findings


def test_include_is_not_expanded_even_when_absolute_file_exists(tmp_path):
    secret = tmp_path / "outside.inc"
    secret.write_text("THIS IS INVALID FORTRAN AND MUST NEVER BE READ")
    source = f"program p\ninclude '{secret.as_posix()}'\nend\n"
    result = analyse_source(source)
    assert result.status == "partial"
    assert result.metrics is None
    assert [(f.rule, f.line) for f in result.findings] == [("FA101", 2)]


def test_continued_include_is_detected():
    result = analyse_source("program p\ninclude &\n& 'missing.inc'\nend\n")
    assert result.status == "partial"
    assert result.findings[0].rule == "FA101"


def test_preprocessor_branches_are_not_combined():
    result = analyse_source(
        "program p\n#ifdef FEATURE\ninteger :: a\n#else\nreal :: a\n#endif\nend\n"
    )
    assert result.status == "partial"
    assert result.metrics is None
    assert {f.rule for f in result.findings} == {"FA102"}


def test_invalid_syntax_is_not_a_clean_report():
    result = analyse_source("program p\nthis is not fortran\nend\n", path="bad.f90")
    assert result.status == "failed"
    assert result.metrics is None
    assert result.findings[0].rule == "FA100"
    assert result.findings[0].line == 2


def test_submodule_needs_host_context():
    result = analyse_source("submodule (parent) child\nend submodule\n")
    assert result.status == "partial"
    assert result.findings[0].rule == "FA103"


def test_fixed_form_continuation():
    result = analyse_source(
        "      SUBROUTINE X\n      IMPLICIT NONE\n      INTEGER A,B,\n     & C,D\n      END\n",
        source_form="fixed",
    )
    assert result.status == "ok"
    assert result.metrics.declared_entities == 4


def test_wrong_source_form_is_configuration_error():
    with pytest.raises(ValueError):
        analyse_source("", source_form="guess")


def test_unnamed_main_program_and_block_data_have_scopes():
    result = analyse_source("integer :: i\ni=1\nend\n")
    assert result.metrics.programs == 1
    assert result.scopes[0].name == "<anonymous>"
    assert result.findings[0].rule == "FA001"
    block = analyse_source("block data b\nimplicit none\ninteger :: i\ncommon /c/ i\nend\n")
    assert block.scopes[0].kind == "block_data"
    assert block.scopes[0].name == "b"
    assert not block.findings


def test_sequential_loops_do_not_accumulate_depth():
    result = analyse_source(
        "subroutine x\nimplicit none\ninteger :: i\n"
        "do i=1,2\nprint *,i\nenddo\ndo i=1,2\nprint *,i\nenddo\nend\n"
    )
    assert result.metrics.loops == 2
    assert result.metrics.max_loop_depth == 1


def test_multiple_declarations_on_one_line_and_array_initialization():
    result = analyse_source(
        "program p\nimplicit none; integer :: a,b\ninteger :: values(2) = [1,2], c\nend\n"
    )
    assert result.status == "ok"
    assert result.metrics.declarations == 2
    assert result.metrics.declared_entities == 4
