# app/compliance/pdf_report.py -- full replacement

"""
Generates a detailed audit PDF. Each decision gets its own block
(not a flat table row) because human-resolved decisions need a
two-stage narrative -- what the engine originally flagged, then who
overrode it and when -- which doesn't fit cleanly into fixed table
columns once both stages are shown.
"""

from fpdf import FPDF


def _safe(value) -> str:
    """
    Coerces None/missing values to a plain ASCII placeholder. Every
    string handed to fpdf's core "helvetica" font must stay within
    Latin-1 -- this is the exact class of bug that crashed the PDF
    route earlier in this session (an em-dash placeholder), so every
    dynamic string goes through this before reaching pdf.cell()/multi_cell().
    """
    if value is None or value == "":
        return "N/A"
    return str(value)


def generate_evidence_pack_pdf(
    company_name: str, period_start: str, period_end: str, decisions: list[dict]
) -> bytes:
    pdf = FPDF()
    pdf.add_page()

    pdf.set_font("Helvetica", "B", 16)
    pdf.cell(0, 10, "Sovereignty Compliance Evidence Report", ln=True)
    pdf.set_font("Helvetica", "", 11)
    pdf.cell(0, 7, f"Company: {_safe(company_name)}", ln=True)
    pdf.cell(0, 7, f"Period: {_safe(period_start)} to {_safe(period_end)}", ln=True)
    pdf.cell(0, 7, f"Total decisions: {len(decisions)}", ln=True)
    pdf.ln(6)

    for i, d in enumerate(decisions, start=1):
        _render_decision_block(pdf, i, d)

    return bytes(pdf.output())


def _render_decision_block(pdf: FPDF, index: int, d: dict) -> None:
    pdf.set_fill_color(235, 235, 235)
    pdf.set_font("Helvetica", "B", 12)
    pdf.cell(0, 8, f"{index}. {_safe(d.get('entity_name'))}", ln=True, fill=True)

    pdf.set_font("Helvetica", "", 10)

    if d.get("model_name") == "human_reviewer":
        _render_human_resolution(pdf, d)
    else:
        _render_engine_decision(pdf, d)

    pdf.ln(4)


def _render_engine_decision(pdf: FPDF, d: dict) -> None:
    """
    A decision the ENGINE made outright (no human override at all) --
    the simple case: outcome, law reference, timestamp.
    """
    pdf.cell(0, 6, f"Decision: {_safe(d.get('decision'))}  (automated, rule-based engine)", ln=True)
    pdf.cell(0, 6, f"Destination: {_safe(d.get('destination_country'))}", ln=True)
    pdf.cell(0, 6, f"Legal reference: Article {_safe(d.get('law_article'))}", ln=True)
    pdf.cell(0, 6, f"Decided at: {_safe(d.get('decided_at'))}", ln=True)


def _render_human_resolution(pdf: FPDF, d: dict) -> None:
    """
    Two-stage narrative: what the system originally flagged and why,
    then who overrode it, to what outcome, and when. This is the
    detail level needed for an auditor to see BOTH the automated
    reasoning and the human accountability trail, not just the final
    outcome.
    """
    pdf.set_font("Helvetica", "I", 10)
    pdf.cell(0, 6, "Stage 1 -- System flagged for review:", ln=True)
    pdf.set_font("Helvetica", "", 10)
    pdf.cell(0, 6, f"  Original outcome: {_safe(d.get('original_decision'))}", ln=True)
    pdf.cell(0, 6, f"  Legal reference: Article {_safe(d.get('original_law_article'))}", ln=True)
    pdf.cell(0, 6, f"  Reason: {_safe(d.get('original_reason_code'))}", ln=True)

    pdf.ln(1)
    pdf.set_font("Helvetica", "I", 10)
    pdf.cell(0, 6, "Stage 2 -- Human review resolution:", ln=True)
    pdf.set_font("Helvetica", "", 10)
    pdf.cell(0, 6, f"  Resolved by: {_safe(d.get('reviewer_name'))} ({_safe(d.get('reviewer_email'))})", ln=True)
    pdf.cell(0, 6, f"  Final decision: {_safe(d.get('decision'))}", ln=True)
    pdf.cell(0, 6, f"  Resolved at: {_safe(d.get('resolved_at'))}", ln=True)
    if d.get("cndp_reference"):
        pdf.cell(0, 6, f"  CNDP reference: {_safe(d.get('cndp_reference'))}", ln=True)
    pdf.cell(0, 6, f"  Destination: {_safe(d.get('destination_country'))}", ln=True)
    