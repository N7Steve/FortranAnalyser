"""AST-based metrics. No compiler, preprocessor or include files are executed/read."""

import re
import threading

from fparser.common.readfortran import FortranStringReader, Line
from fparser.common.sourceinfo import FortranFormat
from fparser.two.parser import ParserFactory
from fparser.two.utils import FortranSyntaxError

from .models import FileResult, Finding, Metrics, Scope

_PARSER_LOCK = threading.Lock()  # fparser's symbol tables are process-global.
_SCOPE_KINDS = {
    "Module": "module",
    "Main_Program": "program",
    "Main_Program0": "program",
    "Block_Data": "block_data",
    "Subroutine_Subprogram": "subroutine",
    "Function_Subprogram": "function",
}
_LOOP_STATEMENTS = {"Label_Do_Stmt", "Nonlabel_Do_Stmt"}
_IGNORED_SCOPES = {"Interface_Block", "Derived_Type_Def"}


class _NoIncludeReader(FortranStringReader):
    """Bypass the reader's automatic INCLUDE expansion, including absolute paths.

    fparser 0.2.5's public next() opens existing include files even when
    include_dirs=[]; _next() returns only the current source's logical items.
    This version-specific adapter is covered by an existing-file include test.
    """

    def next(self, ignore_comments=None):
        if ignore_comments is None:
            ignore_comments = self._ignore_comments
        return self._next(ignore_comments)


def _reader(source: str, source_form: str) -> _NoIncludeReader:
    reader = _NoIncludeReader(source, ignore_comments=False, include_dirs=[])
    reader.set_format(FortranFormat(source_form == "free", False))
    return reader


def _statements(node):
    """Walk syntax contents, not expression items or parent references."""
    if getattr(node, "item", None) is not None:
        yield node
    for child in getattr(node, "content", ()):
        yield from _statements(child)


def _line(node) -> int:
    return node.item.span[0]


def _scope_name(node) -> str:
    first = node.content[0]
    # An unnamed main program starts with its specification/execution part.
    if type(first).__name__ in {"Module_Stmt", "Program_Stmt"}:
        return str(first.items[1])
    if type(first).__name__ in {"Function_Stmt", "Subroutine_Stmt"}:
        return str(first.items[1])
    if type(first).__name__ == "Block_Data_Stmt":
        return str(first.items[0]) if first.items[0] is not None else "<anonymous>"
    return "<anonymous>"


def _owned_statements(node):
    for child in getattr(node, "content", ()):
        if type(child).__name__ in _SCOPE_KINDS or type(child).__name__ in _IGNORED_SCOPES:
            continue
        yield from _owned_statements(child)
        if getattr(child, "item", None) is not None:
            yield child


def _implicit_none(node, inherited: bool | None) -> bool | None:
    implicit = [s for s in _owned_statements(node) if type(s).__name__ == "Implicit_Stmt"]
    if not implicit:
        return inherited
    # An explicit mapping overrides the inherited mapping. NONE(EXTERNAL) alone
    # does not disable implicit typing. Modern NONE(TYPE) is accepted if parsed.
    text = " ".join(str(s).upper() for s in implicit)
    return "IMPLICIT NONE" in text and ("NONE(" not in text.replace(" ", "") or "TYPE" in text)


def _extract(tree, path: str, physical_lines: int) -> FileResult:
    result = FileResult(path, "ok", "", physical_lines)
    totals = {"declarations": 0, "declared_entities": 0, "loops": 0, "calls": 0}
    max_depth = 0

    def visit(node, scope=None, inherited=False, depth=0):
        nonlocal max_depth
        kind = type(node).__name__
        if kind in _IGNORED_SCOPES:
            return  # Interface signatures and type fields are not implementations/local variables.
        if kind in _SCOPE_KINDS:
            stmts = list(_statements(node))
            name = _scope_name(node)
            scope = Scope(
                name=name,
                kind=_SCOPE_KINDS[kind],
                line=_line(stmts[0]),
                end_line=stmts[-1].item.span[1],
                qualified_name=f"{scope.qualified_name}::{name}" if scope else name,
                implicit_none=_implicit_none(node, inherited),
            )
            result.scopes.append(scope)
            inherited = scope.implicit_none
            depth = 0
            if inherited is False:
                result.findings.append(
                    Finding(
                        "FA001",
                        path,
                        scope.line,
                        "warning",
                        f"{scope.kind} {scope.name}: no IMPLICIT NONE propio ni heredado del host.",
                    )
                )
        if kind == "Type_Declaration_Stmt":
            count = len(node.items[2].items)
            totals["declarations"] += 1
            totals["declared_entities"] += count
            if scope:
                scope.declarations += 1
                scope.declared_entities += count
        if kind == "Call_Stmt":
            totals["calls"] += 1
            if scope:
                scope.calls += 1
        # Count loop starts within each construct. Labelled shared-terminal DO
        # statements can be siblings in the same AST block, rather than nested nodes.
        running_depth = depth
        for child in getattr(node, "content", ()):
            if type(child).__name__ in _LOOP_STATEMENTS:
                running_depth += 1
                totals["loops"] += 1
                max_depth = max(max_depth, running_depth)
                if scope:
                    scope.loops += 1
                    scope.max_loop_depth = max(scope.max_loop_depth, running_depth)
                if running_depth == 4:
                    result.findings.append(
                        Finding(
                            "FA002",
                            path,
                            _line(child),
                            "info",
                            "Anidamiento de 4 bucles: revisar legibilidad; no implica por sí solo "
                            "un problema de rendimiento.",
                        )
                    )
            visit(child, scope, inherited, running_depth)

    visit(tree)
    counts = {
        kind: sum(s.kind == kind for s in result.scopes)
        for kind in (
            "function",
            "subroutine",
            "module",
            "program",
        )
    }
    result.metrics = Metrics(
        physical_lines=physical_lines,
        functions=counts["function"],
        subroutines=counts["subroutine"],
        modules=counts["module"],
        programs=counts["program"],
        max_loop_depth=max_depth,
        **totals,
    )
    return result


def analyse_source(source: str, *, path: str = "<memory>", source_form: str = "free") -> FileResult:
    """Analyse one decoded source. For bounded execution use analyse_project().

    Parses syntax, not compiler semantics. Partial files expose no AST metrics.
    """
    if source_form not in {"fixed", "free"}:
        raise ValueError("source_form must be 'fixed' or 'free'")
    physical_lines = len(source.splitlines())
    result = FileResult(path, "ok", source_form, physical_lines)
    with _PARSER_LOCK:
        try:
            # Preflight logical statements, so comments/strings containing INCLUDE
            # or '#' are not confused with actual directives.
            items = list(_reader(source, source_form))
            for item in items:
                text = getattr(item, "line", "").strip()
                if isinstance(item, Line) and re.match(r"(?i)^include\s*['\"]", text):
                    result.findings.append(
                        Finding(
                            "FA101",
                            path,
                            item.span[0],
                            "warning",
                            "INCLUDE no expandido: se necesita contexto del proyecto. "
                            "No se han leído archivos incluidos ni calculado métricas AST.",
                        )
                    )
                elif type(item).__name__ == "CppDirective":
                    result.findings.append(
                        Finding(
                            "FA102",
                            path,
                            item.span[0],
                            "warning",
                            "Directiva de preprocesado no evaluada. Se necesita una fuente "
                            "preprocesada con su configuración; métricas AST no disponibles.",
                        )
                    )
            if result.findings:
                result.status = "partial"
                return result
            parser = ParserFactory().create(std="f2008")
            tree = parser(_reader(source, source_form))
            # Submodule host information is outside this file. Refuse completeness
            # until project-wide host association is implemented.
            if any(type(s).__name__ == "Submodule_Stmt" for s in _statements(tree)):
                result.status = "partial"
                stmt = next(s for s in _statements(tree) if type(s).__name__ == "Submodule_Stmt")
                result.findings.append(
                    Finding(
                        "FA103",
                        path,
                        _line(stmt),
                        "warning",
                        "Submódulo: la asociación con su módulo host aún no está resuelta; "
                        "métricas AST no disponibles.",
                    )
                )
                return result
            result = _extract(tree, path, physical_lines)
            result.source_form = source_form
            return result
        except FortranSyntaxError as exc:
            match = re.search(r"at line (\d+)", str(exc))
            result.status = "failed"
            result.findings.append(
                Finding(
                    "FA100",
                    path,
                    int(match[1]) if match else 1,
                    "error",
                    "El parser no pudo interpretar la fuente: sintaxis inválida o no soportada. "
                    f"{exc}",
                )
            )
            return result
