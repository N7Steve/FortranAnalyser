"""AST structure and decision metrics; never infer control flow from dependencies."""

import re

METHOD = (
    "CC estructural = 1 por unidad ejecutable + IF/ELSE IF + DO con control "
    "+ CASE no DEFAULT + WHERE/FORALL. No cuenta operadores booleanos ni EXIT/CYCLE. "
    "Suma por archivo y proyecto; no es un grafo de flujo de control completo. "
    "Dependencias estáticas: USE, CALL explícito, tipos, herencia y pertenencia. "
    "No resuelve llamadas en expresiones, despacho dinámico, genéricos ni renombrados USE."
)
QUALITY = (
    "Perfil orientativo adaptado (0-10), no equivalencia con la nota Java ni garantía científica: "
    "6 × proporción de ámbitos con IMPLICIT NONE + 2 si profundidad máxima de bucles <= 3 "
    "+ 1 por presencia de EXIT + 1 por presencia de CYCLE. "
    "Los bonus se conceden una vez por archivo; no demuestran que sean necesarios. "
    "Nota global: media de archivos completos; si falta alguno, no se publica nota global."
)


def extract_structure(tree, result):
    from .engine import _SCOPE_KINDS, _scope_name

    nodes, edges, routines = [], [], []
    exits = cycles = 0

    def visit(node, owner=None, routine=None):
        nonlocal exits, cycles
        kind = type(node).__name__
        if kind == "Interface_Block":
            return
        line = getattr(getattr(node, "item", None), "span", (1, 1))[0]
        if kind in _SCOPE_KINDS or kind == "Derived_Type_Def":
            name = (
                str(node.content[0].items[1]) if kind == "Derived_Type_Def" else _scope_name(node)
            )
            qualified = f"{owner['qualified_name']}::{name}" if owner else name
            header = next(c for c in node.content if type(c).__name__ != "Comment")
            current = {
                "id": f"{result.path}::{qualified}".lower(),
                "name": name,
                "qualified_name": qualified,
                "kind": "type" if kind == "Derived_Type_Def" else _SCOPE_KINDS[kind],
                "path": result.path,
                "line": header.item.span[0] if header.item else 1,
            }
            nodes.append(current)
            if owner:
                edges.append(
                    {
                        "source": owner["id"],
                        "target": current["id"],
                        "kind": "contains",
                        "line": current["line"],
                        "resolved": True,
                    }
                )
            owner = current
            routine = None
            if current["kind"] in {"program", "subroutine", "function"}:
                routine = {"name": qualified, "line": current["line"], "complexity": 1}
                routines.append(routine)
        if routine is not None:
            decision = kind in {
                "If_Then_Stmt",
                "Else_If_Stmt",
                "If_Stmt",
                "Where_Stmt",
                "Where_Construct_Stmt",
                "Forall_Stmt",
                "Forall_Construct_Stmt",
            }
            if kind in {"Label_Do_Stmt", "Nonlabel_Do_Stmt"}:
                decision = bool(node.items[-1])
            if kind == "Case_Stmt":
                decision = "DEFAULT" not in str(node).upper()
            routine["complexity"] += int(decision)
            exits += int(kind == "Exit_Stmt")
            cycles += int(kind == "Cycle_Stmt")
        if owner:
            targets = []
            if kind == "Use_Stmt":
                targets.append(("use", str(node.items[2])))
            if kind == "Call_Stmt":
                targets.append(("call", str(node.items[0])))
            if kind == "Derived_Type_Stmt":
                targets.extend(
                    ("extends", x) for x in re.findall(r"EXTENDS\s*\(\s*(\w+)", str(node), re.I)
                )
            if kind == "Data_Component_Def_Stmt" or kind == "Type_Declaration_Stmt":
                targets.extend(
                    ("type", x)
                    for x in re.findall(r"(?:TYPE|CLASS)\s*\(\s*(\w+)", str(node.items[0]), re.I)
                )
            for relation, name in targets:
                edges.append(
                    {
                        "source": owner["id"],
                        "target": name.lower(),
                        "kind": relation,
                        "line": line,
                        "resolved": False,
                    }
                )
        for child in getattr(node, "content", ()):
            visit(child, owner, routine)
        # A single-line IF stores its action statement in items, not content.
        if kind == "If_Stmt":
            visit(node.items[1], owner, routine)

    visit(tree)
    scopes = result.scopes
    implicit = sum(s.implicit_none is True for s in scopes) / len(scopes) if scopes else 0
    score = round(
        6 * implicit + 2 * (result.metrics.max_loop_depth <= 3) + bool(exits) + bool(cycles), 2
    )
    return {
        "nodes": nodes,
        "edges": edges,
        "routines": routines,
        "cyclomatic_complexity": sum(r["complexity"] for r in routines),
        "exit_count": exits,
        "cycle_count": cycles,
        "quality_score": score,
    }


def project_structure(files):
    complete = [f.analysis for f in files if f.status == "ok" and f.analysis is not None]
    nodes = [n for a in complete for n in a["nodes"]]
    edges = [dict(e) for a in complete for e in a["edges"]]
    by_id = {n["id"]: n for n in nodes}
    for edge in edges:
        if edge["resolved"]:
            continue
        kinds = {
            "use": {"module"},
            "call": {"subroutine", "function"},
            "type": {"type"},
            "extends": {"type"},
        }[edge["kind"]]
        candidates = [
            n for n in nodes if n["name"].lower() == edge["target"] and n["kind"] in kinds
        ]
        # Prefer lexical host association; leave ambiguous/external names unresolved.
        source = by_id[edge["source"]]
        local = [
            n
            for n in candidates
            if n["path"] == source["path"]
            and source["qualified_name"]
            .lower()
            .startswith(n["qualified_name"].lower().rsplit("::", 1)[0] + "::")
        ]
        candidates = local or candidates
        if len(candidates) == 1:
            edge.update(target=candidates[0]["id"], resolved=True)
    coverage = len(complete) == len(files)
    return {
        "nodes": nodes,
        "edges": edges,
        "complete": coverage,
        "analysed_files": len(complete),
        "method": METHOD,
        "quality_method": QUALITY,
        "cyclomatic_complexity": sum(a["cyclomatic_complexity"] for a in complete),
        "quality_score": round(sum(a["quality_score"] for a in complete) / len(complete), 2)
        if complete and coverage
        else None,
    }
