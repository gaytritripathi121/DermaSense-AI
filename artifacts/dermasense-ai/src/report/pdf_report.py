from __future__ import annotations

from datetime import datetime, timezone
from pathlib import Path
from uuid import uuid4
from xml.sax.saxutils import escape as xml_escape

from reportlab.lib import colors
from reportlab.lib.enums import TA_LEFT
from reportlab.lib.pagesizes import letter
from reportlab.lib.styles import ParagraphStyle, getSampleStyleSheet
from reportlab.lib.units import inch
from reportlab.platypus import Image, Paragraph, SimpleDocTemplate, Spacer, Table, TableStyle

DISCLAIMER = (
    "DermaSense AI is a screening-support prototype, not a diagnostic device and not a substitute "
    "for professional medical care. No screening output confirms or rules out a condition. "
    "Discuss skin concerns with a qualified clinician."
)
CLASS_LABELS = {
    "ACK": "Actinic keratosis (model class)",
    "BCC": "Basal cell carcinoma (model class)",
    "MEL": "Melanoma (model class)",
    "NEV": "Nevus (model class)",
    "SCC": "Squamous cell carcinoma (model class)",
    "SEK": "Seborrheic keratosis (model class)",
}


def generate_pdf_report(
    output_path: str | Path,
    history: dict,
    image_path: str | Path | None = None,
    prediction: dict | None = None,
    lime_image_path: str | Path | None = None,
    occlusion_image_path: str | Path | None = None,
    explanation_caption: str | None = None,
    history_factors: list[dict] | None = None,
    model_info: dict | None = None,
) -> str:
    """Write a local PDF. The caller decides where the report is stored."""
    output_path = Path(output_path)
    output_path.parent.mkdir(parents=True, exist_ok=True)
    report_id = f"DS-{uuid4().hex[:10].upper()}"
    created_at = datetime.now(timezone.utc).astimezone().strftime("%Y-%m-%d %H:%M %Z")
    styles = getSampleStyleSheet()
    styles.add(ParagraphStyle(name="SectionTitle", parent=styles["Heading2"], textColor=colors.HexColor("#24554e"), spaceBefore=12, spaceAfter=6))
    styles.add(ParagraphStyle(name="SmallBody", parent=styles["BodyText"], fontSize=8.5, leading=12, alignment=TA_LEFT))
    story = [
        Paragraph("DermaSense AI", styles["Title"]),
        Paragraph("Local screening-support report", styles["Heading2"]),
        Paragraph(f"Report ID: {report_id}<br/>Prepared: {created_at}", styles["SmallBody"]),
        Spacer(1, 0.18 * inch),
        Paragraph("Screening-only notice", styles["SectionTitle"]),
        Paragraph(DISCLAIMER, styles["SmallBody"]),
    ]

    story.append(Paragraph("Patient summary", styles["SectionTitle"]))
    summary_rows = [
        ["Initials", history.get("initials") or "Not provided"],
        ["Age", history.get("age") or "Not provided"],
        ["Gender", history.get("gender") or "Not provided"],
        ["Fitzpatrick type", history.get("fitzpatrick") or "Not provided"],
        ["Body region", history.get("region") or "Not provided"],
        ["Lesion diameter (mm)", history.get("diameter") or "Not provided"],
    ]
    table = Table(summary_rows, colWidths=[1.8 * inch, 4.7 * inch], hAlign="LEFT")
    table.setStyle(TableStyle([
        ("BACKGROUND", (0, 0), (0, -1), colors.HexColor("#eef2ec")),
        ("TEXTCOLOR", (0, 0), (-1, -1), colors.HexColor("#29443d")),
        ("GRID", (0, 0), (-1, -1), 0.35, colors.HexColor("#d9dfd6")),
        ("FONTNAME", (0, 0), (0, -1), "Helvetica-Bold"),
        ("FONTSIZE", (0, 0), (-1, -1), 8.5),
        ("VALIGN", (0, 0), (-1, -1), "TOP"),
        ("PADDING", (0, 0), (-1, -1), 6),
    ]))
    story.append(table)

    history_rows = [
        [name, str(history.get(key) or "Not provided")]
        for key, name in [
            ("smoking", "Smoking exposure"),
            ("alcohol", "Alcohol exposure"),
            ("pesticide", "Pesticide exposure"),
            ("personalCancer", "Personal skin-cancer history"),
            ("familyCancer", "Family cancer history"),
            ("itch", "Itch"),
            ("growth", "Growth"),
            ("pain", "Pain"),
            ("change", "Change"),
            ("bleeding", "Bleeding"),
            ("elevation", "Elevation"),
        ]
    ]
    story.extend([Paragraph("History notes", styles["SectionTitle"]), Table(history_rows, colWidths=[2.4 * inch, 4.1 * inch])])

    if image_path and Path(image_path).exists():
        story.append(Paragraph("Uploaded image", styles["SectionTitle"]))
        story.append(Image(str(image_path), width=3.2 * inch, height=3.2 * inch, kind="proportional"))

    story.append(Paragraph("Screening status", styles["SectionTitle"]))
    if prediction and prediction.get("status") not in {"model_unavailable", "not_connected"}:
        top_three = prediction.get("top_three", [])
        code = prediction.get("predicted_class") or (top_three[0].get("class_code") if top_three else None)
        confidence = prediction.get("confidence")
        if confidence is None and top_three:
            confidence = top_three[0].get("probability")
        if code:
            class_label = CLASS_LABELS.get(str(code), "Unmapped model class")
            story.append(Paragraph(
                f"{class_label}; calibrated confidence: {float(confidence):.1%}"
                if confidence is not None
                else class_label,
                styles["SmallBody"],
            ))
        else:
            story.append(Paragraph(
                xml_escape(str(prediction.get("warning", "No usable screening result is available."))),
                styles["SmallBody"],
            ))
        if prediction.get("status") == "low_confidence":
            story.append(Paragraph(
                "LOW CONFIDENCE: the result is unreliable. Please consult a dermatologist.",
                styles["SmallBody"],
            ))
        if top_three:
            rows = [["Model class", "Probability"]]
            rows.extend(
                [CLASS_LABELS.get(str(item["class_code"]), str(item["class_code"])), f"{float(item['probability']):.1%}"]
                for item in top_three[:3]
            )
            story.append(Table(rows, colWidths=[4.8 * inch, 1.7 * inch]))
    else:
        story.append(Paragraph(
            "No model result is available. No diagnosis, risk estimate, or image explanation was generated.",
            styles["SmallBody"],
        ))

    if lime_image_path and Path(lime_image_path).exists():
        story.extend([Paragraph("LIME visual explanation", styles["SectionTitle"]), Image(str(lime_image_path), width=3.2 * inch, height=3.2 * inch, kind="proportional")])
    if occlusion_image_path and Path(occlusion_image_path).exists():
        story.extend([Paragraph("Occlusion sensitivity", styles["SectionTitle"]), Image(str(occlusion_image_path), width=3.2 * inch, height=3.2 * inch, kind="proportional")])
    if explanation_caption:
        story.append(Paragraph(xml_escape(explanation_caption), styles["SmallBody"]))
    if history_factors:
        story.append(Paragraph("History feature sensitivity", styles["SectionTitle"]))
        story.append(Table(
            [["Feature", "Score change"], *[[str(item.get("feature", "")), f"{float(item.get('score_change', 0)):+.4f}"] for item in history_factors]],
            colWidths=[4.8 * inch, 1.7 * inch],
        ))
        story.append(Paragraph("Feature sensitivity describes model behavior; it is not causal or clinical evidence.", styles["SmallBody"]))

    story.extend([
        Paragraph("General next step", styles["SectionTitle"]),
        Paragraph(
            "Use these notes to support a conversation with a qualified clinician. "
            "If a spot is rapidly changing, bleeding, painful, or otherwise concerning, seek medical advice.",
            styles["SmallBody"],
        ),
        Spacer(1, 0.16 * inch),
        Paragraph(
            xml_escape(
                f"Model version: {(model_info or {}).get('version', 'not connected')} · "
                f"Dataset: {(model_info or {}).get('dataset', 'not evaluated')} · "
                f"Test metrics: {(model_info or {}).get('metrics_summary', 'not available')}"
            ),
            styles["SmallBody"],
        ),
    ])
    SimpleDocTemplate(str(output_path), pagesize=letter, title="DermaSense AI report").build(story)
    return report_id
