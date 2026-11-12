"""Paginated, escaped PDF export of the reusable report contract."""

import hashlib
import io
import json
from xml.sax.saxutils import escape

from reportlab.graphics.shapes import Drawing, Line, Polygon, Rect, String
from reportlab.lib import colors
from reportlab.lib.styles import getSampleStyleSheet
from reportlab.platypus import Paragraph, SimpleDocTemplate, Spacer


def render_report(report, name="Proyecto"):
    buffer = io.BytesIO()
    styles = getSampleStyleSheet()
    styles["Title"].textColor = colors.HexColor("#a94b08")
    styles["BodyText"].wordWrap = "CJK"
    story = []

    def text(value, style="BodyText"):
        story.append(Paragraph(escape(str(value)), styles[style]))
        story.append(Spacer(1, 6))

    text("FortranAnalyser", "Title")
    text(name, "Heading1")
    text(f"Parser: {report['parser']} | Reglas: {report['rules_version']}")
    text("Resumen: " + " | ".join(f"{k}: {v}" for k, v in report["summary"].items()))
    a = report.get("analysis")
    if a:
        text("Calidad y complejidad", "Heading1")
        quality = a["quality_score"] if a["quality_score"] is not None else "N/D"
        text(
            f"CC {'total' if a['complete'] else 'parcial'}: {a['cyclomatic_complexity']}. "
            f"Nota orientativa / 10: {quality}."
        )
        text(a["method"])
        text(a["quality_method"])
        text("Diagrama de clases y grafo de dependencias", "Heading1")
        text(
            "Tipos derivados, módulos y rutinas; flechas origen -> destino. "
            "contains: pertenencia; use: importación; call: llamada; "
            "type: referencia a tipo (no garantiza propiedad); extends: herencia. "
            "El grafo no representa flujo de control."
        )
        names = {n["id"]: n for n in a["nodes"]}
        # Small graph pages keep labels readable; cross-page edges follow below.
        for offset in range(0, len(a["nodes"]), 8):
            batch = a["nodes"][offset : offset + 8]
            height = len(batch) * 55 + 15
            drawing = Drawing(480, height)
            positions = {}
            for i, n in enumerate(batch):
                y = height - i * 55 - 45
                positions[n["id"]] = y + 18
                drawing.add(Rect(0, y, 300, 40, fillColor=colors.HexColor("#fff0db")))
                drawing.add(String(8, y + 25, f"{n['kind']}: {n['name']}"[:65], fontSize=9))
                drawing.add(String(8, y + 10, f"{n['path']}:{n['line']}"[:75], fontSize=8))
            for i, e in enumerate(a["edges"]):
                if e["source"] in positions and e["target"] in positions:
                    y1, y2 = positions[e["source"]], positions[e["target"]]
                    x = 320 + (i % 5) * 25
                    for x1, yy1, x2, yy2 in [(300, y1, x, y1), (x, y1, x, y2), (x, y2, 300, y2)]:
                        drawing.add(Line(x1, yy1, x2, yy2, strokeColor=colors.HexColor("#a94b08")))
                    drawing.add(
                        Polygon(
                            [300, y2, 307, y2 + 3, 307, y2 - 3],
                            fillColor=colors.HexColor("#a94b08"),
                        )
                    )
            story.append(drawing)
            story.append(Spacer(1, 12))
        for e in a["edges"]:
            src = names[e["source"]]
            dst = names.get(e["target"])
            label = (
                f"{dst['qualified_name']} ({dst['path']})"
                if dst
                else e["target"] + " [externo / no resuelto]"
            )
            text(f"{src['qualified_name']} ({src['path']}:{e['line']}) --{e['kind']}--> {label}")
    else:
        text("Informe anterior: vuelve a analizar para obtener estructura y complejidad.")
    for file in report["files"]:
        text(file["path"], "Heading1")
        text(
            f"Estado: {file['status']}; formato: {file['source_form']}; "
            f"líneas: {file['physical_lines']}"
        )
        if file["metrics"]:
            text("Métricas: " + "; ".join(f"{k}: {v}" for k, v in file["metrics"].items()))
        fa = file.get("analysis")
        if fa:
            text(
                f"CC: {fa['cyclomatic_complexity']} | Nota / 10: {fa['quality_score']} | "
                f"EXIT: {fa['exit_count']} | CYCLE: {fa['cycle_count']}"
            )
            for r in fa["routines"]:
                text(f"{r['name']}:{r['line']} - CC {r['complexity']}")
        for scope in file["scopes"]:
            text(
                f"{scope['kind']} {scope['qualified_name']}: "
                f"líneas {scope['line']}-{scope['end_line']}"
            )
        for f in file["findings"]:
            text(f"{f['rule']} | {f['severity']} | {f['path']}:{f['line']} | {f['message']}")
        if not file["findings"]:
            text("Sin hallazgos emitidos. Consultar estado y límites del análisis.")
    text("Firma virtual de FortranAnalyser", "Heading1")
    text("Sello visual generado por FortranAnalyser. No es una firma digital con certificado.")
    digest = hashlib.sha256(
        json.dumps(report, sort_keys=True, ensure_ascii=True).encode()
    ).hexdigest()
    text("SHA-256 del informe JSON canónico: " + digest)
    text("Basado en FortranAnalyser de Michael García Rodríguez. GPL-3.0-or-later.")

    def footer(canvas, doc):
        canvas.setFont("Helvetica", 8)
        canvas.setFillColor(colors.HexColor("#a94b08"))
        canvas.drawString(40, 24, "FortranAnalyser | Firma virtual / sello visual")
        canvas.drawRightString(555, 24, f"Página {doc.page}")

    SimpleDocTemplate(
        buffer,
        title="FortranAnalyser - Informe",
        author="FortranAnalyser",
        leftMargin=40,
        rightMargin=40,
        topMargin=40,
        bottomMargin=42,
    ).build(story, onFirstPage=footer, onLaterPages=footer)
    return buffer.getvalue()
