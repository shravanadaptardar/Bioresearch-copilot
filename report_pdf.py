"""
report_pdf.py
Generates a clean PDF research report from the pipeline result dict.
Uses reportlab — pip install reportlab
"""
from reportlab.lib.pagesizes import A4
from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
from reportlab.lib.units import cm
from reportlab.lib import colors
from reportlab.platypus import (
    SimpleDocTemplate, Paragraph, Spacer, Table, TableStyle,
    HRFlowable, Preformatted
)
from reportlab.lib.enums import TA_LEFT, TA_CENTER
import io
from datetime import date

# ── Colour palette ────────────────────────────────────────────────────────────
BLUE   = colors.HexColor("#1f6feb")
DBLUE  = colors.HexColor("#0d1117")
LGRAY  = colors.HexColor("#f6f8fa")
MGRAY  = colors.HexColor("#8b949e")
BLACK  = colors.HexColor("#24292f")
GREEN  = colors.HexColor("#2ea043")


def _styles():
    base = getSampleStyleSheet()
    s = {}
    s["title"] = ParagraphStyle("title",
        fontSize=22, textColor=BLUE, spaceAfter=10,
        fontName="Helvetica-Bold", alignment=TA_LEFT, leading=26)
    s["subtitle"] = ParagraphStyle("subtitle",
        fontSize=10, textColor=MGRAY, spaceAfter=16,
        fontName="Helvetica", alignment=TA_LEFT, leading=14)
    s["section"] = ParagraphStyle("section",
        fontSize=12, textColor=BLUE, spaceBefore=14, spaceAfter=8,
        fontName="Helvetica-Bold", leading=16)
    s["body"] = ParagraphStyle("body",
        fontSize=9, textColor=BLACK, spaceAfter=4,
        fontName="Helvetica", leading=14)
    s["paper_title"] = ParagraphStyle("paper_title",
        fontSize=9, textColor=colors.HexColor("#0550ae"),
        fontName="Helvetica-Bold", spaceAfter=2)
    s["meta"] = ParagraphStyle("meta",
        fontSize=8, textColor=MGRAY, fontName="Helvetica", spaceAfter=6)
    s["code"] = ParagraphStyle("code",
        fontSize=7.5, textColor=BLACK, fontName="Courier",
        backColor=LGRAY, leading=11, leftIndent=8, spaceAfter=2)
    return s


def _hr(story):
    story.append(HRFlowable(width="100%", thickness=0.5,
                             color=colors.HexColor("#d0d7de"), spaceAfter=8))


def generate_pdf(query: str, result: dict) -> bytes:
    buf = io.BytesIO()
    doc = SimpleDocTemplate(buf, pagesize=A4,
        leftMargin=2*cm, rightMargin=2*cm,
        topMargin=2*cm, bottomMargin=2*cm)

    s     = _styles()
    story = []

    # ── Header ────────────────────────────────────────────────────────────────
    story.append(Paragraph("BioResearch Copilot", s["title"]))
    story.append(Paragraph(f"Generated: {date.today().isoformat()}  ·  Query: {query[:120]}", s["subtitle"]))
    _hr(story)

    # ── Plan badges ───────────────────────────────────────────────────────────
    plan = result.get("plan", {})
    if plan:
        domain  = plan.get("domain", "")
        genes   = ", ".join(plan.get("genes", []))
        disease = plan.get("disease_context", "")
        badge_text = f"Domain: {domain}"
        if genes:    badge_text += f"  ·  Genes: {genes}"
        if disease:  badge_text += f"  ·  Disease: {disease}"
        story.append(Paragraph(badge_text, s["meta"]))
        story.append(Spacer(1, 6))

    # ── Literature ────────────────────────────────────────────────────────────
    papers = result.get("literature", [])
    if papers:
        story.append(Paragraph("Literature", s["section"]))
        for p in papers:
            story.append(Paragraph(p.get("title", "No title"), s["paper_title"]))
            if p.get("summary"):
                story.append(Paragraph(p["summary"], s["body"]))
            meta = f"{p.get('authors','')}  ·  {p.get('journal','')}  {p.get('year','')}  ·  PMID: {p.get('pmid','')}"
            story.append(Paragraph(meta.strip(" ·"), s["meta"]))
        _hr(story)

    # ── Datasets ──────────────────────────────────────────────────────────────
    datasets = result.get("datasets", [])
    if datasets:
        story.append(Paragraph("Relevant Datasets (GEO)", s["section"]))
        table_data = [["Accession", "Samples", "Title"]]
        for d in datasets:
            table_data.append([
                d.get("accession",""),
                str(d.get("samples","?")),
                d.get("title","")[:80],
            ])
        tbl = Table(table_data, colWidths=[3*cm, 2*cm, 12*cm])
        tbl.setStyle(TableStyle([
            ("BACKGROUND", (0,0), (-1,0), BLUE),
            ("TEXTCOLOR",  (0,0), (-1,0), colors.white),
            ("FONTNAME",   (0,0), (-1,0), "Helvetica-Bold"),
            ("FONTSIZE",   (0,0), (-1,-1), 8),
            ("ROWBACKGROUNDS", (0,1),(-1,-1), [colors.white, LGRAY]),
            ("GRID",       (0,0),(-1,-1), 0.25, colors.HexColor("#d0d7de")),
            ("VALIGN",     (0,0),(-1,-1), "MIDDLE"),
            ("TOPPADDING", (0,0),(-1,-1), 4),
            ("BOTTOMPADDING",(0,0),(-1,-1), 4),
        ]))
        story.append(tbl)
        story.append(Spacer(1, 8))
        _hr(story)

    # ── Workflow ──────────────────────────────────────────────────────────────
    workflow = result.get("workflow", [])
    if workflow:
        story.append(Paragraph("Suggested Workflow", s["section"]))
        for i, step in enumerate(workflow, 1):
            story.append(Paragraph(
                f"<b>{i}.</b> {step.get('step','')}  <font color='#8b949e'>({step.get('tool','')})</font>",
                s["body"]))
        _hr(story)

    # ── Tools ─────────────────────────────────────────────────────────────────
    tools = result.get("tools", [])
    if tools:
        story.append(Paragraph("Recommended Tools", s["section"]))
        story.append(Paragraph("  ·  ".join(tools), s["body"]))
        _hr(story)

    # ── Marker interpretation ─────────────────────────────────────────────────
    marker = result.get("marker_interpretation", "")
    if marker:
        story.append(Paragraph("Marker Interpretation", s["section"]))
        story.append(Paragraph(marker, s["body"]))
        _hr(story)

    # ── Experimental notes ────────────────────────────────────────────────────
    exp = result.get("experimental_notes", "")
    if exp:
        story.append(Paragraph("Experimental Considerations", s["section"]))
        story.append(Paragraph(exp, s["body"]))
        _hr(story)

    # ── Code template ─────────────────────────────────────────────────────────
    code = result.get("code_template", "")
    if code:
        story.append(Paragraph("Python / Scanpy Code Template", s["section"]))
        # Split into lines, wrap each as Preformatted
        for line in code.split("\n"):
            story.append(Preformatted(line if line else " ", s["code"]))

    doc.build(story)
    buf.seek(0)
    return buf.read()
