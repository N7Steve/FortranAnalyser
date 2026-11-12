from fortran_analyser.engine import analyse_source
from fortran_analyser.models import FileResult
from fortran_analyser.structure import project_structure

SOURCE = """module shapes
implicit none
type :: base
integer :: x
end type
type, extends(base) :: child
type(base) :: b
end type
contains
subroutine work(n)
integer :: n, i
do i=1,n
if (i == 2) cycle
if (i == 3) then
exit
else if (i == 4) then
call external_job()
end if
end do
select case(n)
case(1)
case default
end select
end subroutine
end module
"""


def test_ast_graph_complexity_and_quality():
    r = analyse_source(SOURCE, path="shapes.f90")
    assert r.status == "ok"
    a = r.analysis
    assert a["cyclomatic_complexity"] == 6  # base + DO + IF + IF + ELSE IF + CASE
    assert a["exit_count"] == a["cycle_count"] == 1
    assert a["quality_score"] == 10
    project = project_structure([r])
    assert project["quality_score"] == 10
    assert {n["kind"] for n in project["nodes"]} == {"module", "type", "subroutine"}
    assert {e["kind"] for e in project["edges"]} >= {"extends", "type", "contains", "call"}
    assert all(e["resolved"] for e in project["edges"] if e["kind"] in {"type", "extends"})
    assert not next(e for e in project["edges"] if e["kind"] == "call")["resolved"]


def test_bonuses_once_and_not_from_strings_or_comments():
    source = """program p
implicit none
integer :: i
do i=1,3
print *, 'exit cycle if'
! exit cycle
end do
end
"""
    a = analyse_source(source).analysis
    assert a["exit_count"] == a["cycle_count"] == 0
    assert a["quality_score"] == 8
    assert a["cyclomatic_complexity"] == 2


def test_partial_project_never_gets_a_global_score():
    r = analyse_source(SOURCE, path="a.f90")
    project = project_structure([r, FileResult("bad.f90", "failed", "free")])
    assert project["complete"] is False
    assert project["quality_score"] is None
    assert project["analysed_files"] == 1


def test_cross_file_use_and_ambiguous_calls():
    mod = analyse_source("module m\nimplicit none\nend module", path="m.f90")
    main = analyse_source("program p\nuse m\nimplicit none\ncall work()\nend", path="p.f90")
    routines = [analyse_source("subroutine work()\nend", path=p) for p in ["a.f90", "b.f90"]]
    a = project_structure([mod, main, *routines])
    assert next(e for e in a["edges"] if e["kind"] == "use")["resolved"]
    assert not next(e for e in a["edges"] if e["kind"] == "call")["resolved"]


def test_plain_do_has_no_condition_and_internal_scopes_have_own_base():
    source = """program p
implicit none
do
exit
end do
contains
subroutine s
if (.true.) return
end subroutine
end
"""
    a = analyse_source(source).analysis
    assert [r["complexity"] for r in a["routines"]] == [1, 2]
    assert a["cyclomatic_complexity"] == 3


def test_comment_before_function_header_keeps_name_and_line():
    source = """module m
implicit none
contains
subroutine s
end subroutine
! function documentation
real function answer()
answer = 42
end function
end module
"""
    r = analyse_source(source)
    assert r.status == "ok"
    assert [x["name"] for x in r.analysis["routines"]] == ["m::s", "m::answer"]
    assert r.analysis["routines"][1]["line"] == 7


def test_repeated_exit_cycle_do_not_multiply_bonus():
    source = """program p
implicit none
do
if (.true.) cycle
if (.true.) cycle
if (.true.) exit
exit
end do
end
"""
    a = analyse_source(source).analysis
    assert a["exit_count"] == a["cycle_count"] == 2
    assert a["quality_score"] == 10
