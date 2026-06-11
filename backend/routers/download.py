"""POST /api/download/{format} — gera arquivo para download a partir de um texto.

Nota: a spec original sugeria GET, mas GET com body não é suportado de forma
confiável por browsers/proxies — usamos POST com o mesmo contrato.

O conversor markdown→PDF usa reportlab.platypus (layout com quebra de linha e
paginação automáticas): tabelas estilizadas com cabeçalho repetido, blocos de
código com quebra de linha, listas, citações e rodapé com número de página.
Emojis são sanitizados (as fontes padrão do PDF não têm esses glifos).
"""

import io
import re
import textwrap

from fastapi import APIRouter, HTTPException
from fastapi.responses import Response
from pydantic import BaseModel

router = APIRouter()


class DownloadRequest(BaseModel):
    content: str


# ===== Sanitização: as fontes padrão (WinAnsi/cp1252) não têm emoji =====
_SYMBOL_MAP = {
    "✓": "v", "✔": "v", "✗": "x", "✘": "x", "•": "-", "·": "-",
    "→": "->", "←": "<-", "⇒": "=>", "—": "-", "–": "-",
    "“": '"', "”": '"', "‘": "'", "’": "'", "…": "...",
    "█": "", "■": "", "▪": "", "▸": "", "▾": "",
}


def _sanitize(text: str) -> str:
    for k, v in _SYMBOL_MAP.items():
        text = text.replace(k, v)
    # remove o que não é representável em cp1252 (emoji etc.) p/ não virar ■
    return text.encode("cp1252", errors="ignore").decode("cp1252")


def _esc(s: str) -> str:
    """Escapa XML e converte markdown inline (negrito/itálico/código)."""
    s = s.replace("&", "&amp;").replace("<", "&lt;").replace(">", "&gt;")
    s = re.sub(r"\*\*(.+?)\*\*", r"<b>\1</b>", s)
    s = re.sub(r"(?<!\*)\*([^*]+)\*(?!\*)", r"<i>\1</i>", s)
    s = re.sub(r"`([^`]+)`", r"<font face='Courier' size='9'>\1</font>", s)
    return s


def _is_table_row(line: str) -> bool:
    s = line.strip()
    return s.startswith("|") and s.endswith("|") and s.count("|") >= 2


def _split_row(line: str) -> list[str]:
    return [c.strip() for c in line.strip().strip("|").split("|")]


def _markdown_to_pdf(content: str) -> bytes:
    from reportlab.lib import colors
    from reportlab.lib.enums import TA_JUSTIFY
    from reportlab.lib.pagesizes import A4
    from reportlab.lib.styles import ParagraphStyle, getSampleStyleSheet
    from reportlab.lib.units import cm
    from reportlab.platypus import (
        KeepTogether,
        Paragraph,
        Preformatted,
        SimpleDocTemplate,
        Spacer,
        Table,
        TableStyle,
    )

    content = _sanitize(content)

    buf = io.BytesIO()
    doc = SimpleDocTemplate(
        buf, pagesize=A4,
        leftMargin=2 * cm, rightMargin=2 * cm,
        topMargin=2 * cm, bottomMargin=2 * cm,
        title="Documento",
    )
    usable_width = A4[0] - 4 * cm

    styles = getSampleStyleSheet()
    accent = colors.HexColor("#1F4788")

    title_style = ParagraphStyle(
        "DocTitle", parent=styles["Heading1"], fontSize=20, leading=24,
        textColor=accent, spaceAfter=14,
    )
    h2 = ParagraphStyle(
        "H2", parent=styles["Heading2"], textColor=accent, spaceBefore=14, spaceAfter=6,
    )
    h3 = ParagraphStyle(
        "H3", parent=styles["Heading3"], spaceBefore=10, spaceAfter=4,
    )
    body = ParagraphStyle(
        "Body", parent=styles["Normal"], fontSize=10.5, leading=15,
        alignment=TA_JUSTIFY, spaceAfter=6,
    )
    bullet = ParagraphStyle(
        "Bullet", parent=body, leftIndent=16, bulletIndent=6, alignment=0, spaceAfter=3,
    )
    quote = ParagraphStyle(
        "Quote", parent=body, leftIndent=14, textColor=colors.HexColor("#555555"),
        fontName="Helvetica-Oblique", borderPadding=4,
    )
    code_style = ParagraphStyle(
        "CodeBlock", parent=styles["Code"], fontSize=8, leading=10.5,
        backColor=colors.HexColor("#f4f4f4"), borderPadding=8,
        borderColor=colors.HexColor("#dddddd"), borderWidth=0.5,
    )
    cell_style = ParagraphStyle("Cell", parent=styles["Normal"], fontSize=9, leading=12)
    cell_head = ParagraphStyle(
        "CellHead", parent=cell_style, textColor=colors.white, fontName="Helvetica-Bold",
    )

    def make_table(rows: list[list[str]]):
        """Tabela markdown → platypus Table estilizada (cabeçalho + zebra)."""
        ncols = max(len(r) for r in rows)
        data = []
        for i, r in enumerate(rows):
            r = r + [""] * (ncols - len(r))
            sty = cell_head if i == 0 else cell_style
            data.append([Paragraph(_esc(c), sty) for c in r])
        table = Table(
            data,
            colWidths=[usable_width / ncols] * ncols,
            repeatRows=1,  # cabeçalho repete quando a tabela quebra de página
        )
        zebra = [colors.white, colors.HexColor("#eef2f8")]
        table.setStyle(TableStyle([
            ("BACKGROUND", (0, 0), (-1, 0), accent),
            ("ROWBACKGROUNDS", (0, 1), (-1, -1), zebra),
            ("GRID", (0, 0), (-1, -1), 0.4, colors.HexColor("#c5cdd8")),
            ("VALIGN", (0, 0), (-1, -1), "MIDDLE"),
            ("TOPPADDING", (0, 0), (-1, -1), 5),
            ("BOTTOMPADDING", (0, 0), (-1, -1), 5),
            ("LEFTPADDING", (0, 0), (-1, -1), 7),
            ("RIGHTPADDING", (0, 0), (-1, -1), 7),
        ]))
        return table

    flow = []
    lines = content.split("\n")
    i = 0
    saw_title = False
    in_code = False
    code_lines: list[str] = []

    def flush_code():
        if code_lines:
            wrapped = []
            for ln in code_lines:
                wrapped.extend(textwrap.wrap(
                    ln, width=95, drop_whitespace=False,
                    subsequent_indent="    ",
                ) or [""])
            flow.append(Preformatted("\n".join(wrapped), code_style))
            flow.append(Spacer(1, 8))
            code_lines.clear()

    while i < len(lines):
        line = lines[i]
        stripped = line.strip()

        # blocos de código
        if stripped.startswith("```"):
            if in_code:
                flush_code()
            in_code = not in_code
            i += 1
            continue
        if in_code:
            code_lines.append(line)
            i += 1
            continue

        # tabelas markdown
        if _is_table_row(line):
            rows = []
            while i < len(lines) and _is_table_row(lines[i]):
                cells = _split_row(lines[i])
                # pula a linha separadora |---|---|
                if not all(re.fullmatch(r":?-{2,}:?", c) for c in cells):
                    rows.append(cells)
                i += 1
            if rows:
                tbl = make_table(rows)
                # tabela pequena não deve ser cortada no meio da página
                flow.append(KeepTogether([tbl]) if len(rows) <= 12 else tbl)
                flow.append(Spacer(1, 10))
            continue

        if not stripped:
            flow.append(Spacer(1, 5))
        elif stripped.startswith("### "):
            flow.append(Paragraph(_esc(stripped[4:]), h3))
        elif stripped.startswith("## "):
            flow.append(Paragraph(_esc(stripped[3:]), h2))
        elif stripped.startswith("# "):
            style = h2 if saw_title else title_style
            saw_title = True
            flow.append(Paragraph(_esc(stripped[2:]), style))
        elif stripped.startswith(("- ", "* ")):
            flow.append(Paragraph(_esc(stripped[2:]), bullet, bulletText="-"))
        elif re.match(r"^\d+[.)]\s", stripped):
            num, rest = re.match(r"^(\d+)[.)]\s+(.*)$", stripped).groups()
            flow.append(Paragraph(_esc(rest), bullet, bulletText=f"{num}."))
        elif stripped.startswith("> "):
            flow.append(Paragraph(_esc(stripped[2:]), quote))
        elif set(stripped) <= {"-", "_", "*"} and len(stripped) >= 3:
            flow.append(Spacer(1, 8))  # linha horizontal vira respiro
        else:
            flow.append(Paragraph(_esc(stripped), body))
        i += 1

    if in_code:
        flush_code()  # bloco não fechado

    def footer(canvas, doc_):
        canvas.saveState()
        canvas.setFont("Helvetica", 8)
        canvas.setFillColor(colors.HexColor("#888888"))
        canvas.drawRightString(A4[0] - 2 * cm, 1.1 * cm, f"Página {doc_.page}")
        canvas.restoreState()

    doc.build(flow, onFirstPage=footer, onLaterPages=footer)
    return buf.getvalue()


@router.post("/api/download/{format}")
async def download(format: str, req: DownloadRequest):
    if format == "txt":
        return Response(
            req.content.encode("utf-8"),
            media_type="text/plain; charset=utf-8",
            headers={"Content-Disposition": "attachment; filename=resposta.txt"},
        )
    if format == "md":
        return Response(
            req.content.encode("utf-8"),
            media_type="text/markdown; charset=utf-8",
            headers={"Content-Disposition": "attachment; filename=resposta.md"},
        )
    if format == "pdf":
        try:
            pdf = _markdown_to_pdf(req.content)
        except Exception as e:
            raise HTTPException(500, f"Falha ao gerar PDF: {e}")
        return Response(
            pdf,
            media_type="application/pdf",
            headers={"Content-Disposition": "attachment; filename=resposta.pdf"},
        )
    raise HTTPException(400, "Formato inválido. Use: txt, md ou pdf")
