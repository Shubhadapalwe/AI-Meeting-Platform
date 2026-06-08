from pathlib import Path
from datetime import datetime
import json

from reportlab.lib.pagesizes import A4
from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
from reportlab.lib.units import inch
from reportlab.platypus import SimpleDocTemplate, Paragraph, Spacer, Table, TableStyle
from reportlab.lib import colors

from app.services.meeting_aggregation_service import aggregate_meeting_transcripts

BACKEND_ROOT = Path(__file__).resolve().parent.parent.parent
STORAGE_DIR = BACKEND_ROOT / "storage"

TRANSCRIPTS_DIR = STORAGE_DIR / "transcripts"
SUMMARIES_DIR = STORAGE_DIR / "summaries"
PDF_DIR = STORAGE_DIR / "pdfs"
MEETINGS_DIR = STORAGE_DIR / "meetings"

PDF_DIR.mkdir(parents=True, exist_ok=True)
SUMMARIES_DIR.mkdir(parents=True, exist_ok=True)
MEETINGS_DIR.mkdir(parents=True, exist_ok=True)


def load_latest_json(folder: Path, meeting_id: str):
    files = list(folder.glob(f"{meeting_id}_*.json"))

    if not files:
        return None

    files.sort(key=lambda file: file.stat().st_mtime, reverse=True)

    for f_path in files:
        try:
            with open(f_path, "r", encoding="utf-8") as f:
                return json.load(f)
        except Exception:
            continue  # skip corrupted/empty files

    return None


def safe_text(value):
    if value is None:
        return ""

    return (
        str(value)
        .replace("&", "&amp;")
        .replace("<", "&lt;")
        .replace(">", "&gt;")
    )


def auto_generate_summary(meeting_id: str, transcript: dict):
    import re
    full_text = transcript.get("full_text", "")
    words = full_text.split()
    sentences = re.split(r"(?<=[.!?])\s+", full_text)

    short = " ".join(words[:50]) + ("..." if len(words) > 50 else "")

    action_kw = ["will", "should", "need to", "must", "going to", "action", "task", "follow up"]
    action_items = [s.strip() for s in sentences if any(k in s.lower() for k in action_kw)][:5]
    if not action_items:
        action_items = ["Review meeting notes and follow up on discussed topics."]

    decision_kw = ["decided", "agreed", "confirmed", "resolved", "approved", "chosen"]
    decisions = [s.strip() for s in sentences if any(k in s.lower() for k in decision_kw)][:5]
    if not decisions:
        decisions = ["No explicit decisions detected."]

    parsed = {
        "meeting_id": meeting_id,
        "short_summary": short,
        "key_topics": [],
        "action_items": action_items,
        "decisions": decisions,
        "generated_by": "extractive_fallback",
        "created_at": datetime.now().isoformat(timespec="seconds"),
        "word_count": len(words),
    }

    summary_path = SUMMARIES_DIR / f"{meeting_id}_auto_summary.json"
    with open(summary_path, "w", encoding="utf-8") as f:
        json.dump(parsed, f, indent=2, ensure_ascii=False)

    return parsed


def generate_meeting_minutes_pdf(meeting_id: str):


    # Always regenerate merged transcript before PDF generation.
    # This ensures latest speaker diarization and participant names.
    transcript = aggregate_meeting_transcripts(meeting_id)

    if not transcript:
        raise FileNotFoundError(
            "No transcript found. Generate transcript first."
        )

    summary = load_latest_json(
        SUMMARIES_DIR,
        meeting_id,
    )

    if not summary:
        summary = auto_generate_summary(
            meeting_id,
            transcript,
        )

    pdf_path = PDF_DIR / f"meeting_minutes_{meeting_id}.pdf"

    doc = SimpleDocTemplate(
        str(pdf_path),
        pagesize=A4,
        rightMargin=40,
        leftMargin=40,
        topMargin=40,
        bottomMargin=40,
    )

    styles = getSampleStyleSheet()

    title_style = ParagraphStyle(
        "TitleStyle",
        parent=styles["Title"],
        fontSize=22,
        spaceAfter=18,
        textColor=colors.HexColor("#0f172a"),
    )

    heading_style = ParagraphStyle(
        "HeadingStyle",
        parent=styles["Heading2"],
        fontSize=14,
        spaceBefore=14,
        spaceAfter=8,
        textColor=colors.HexColor("#2563eb"),
    )

    normal_style = ParagraphStyle(
        "NormalStyle",
        parent=styles["BodyText"],
        fontSize=10,
        leading=14,
    )

    small_style = ParagraphStyle(
        "SmallStyle",
        parent=styles["BodyText"],
        fontSize=9,
        leading=12,
    )

    story = []

    story.append(Paragraph("AI Meeting Minutes", title_style))
    story.append(Paragraph(f"<b>Meeting ID:</b> {safe_text(meeting_id)}", normal_style))

    story.append(
        Paragraph(
            f"<b>Generated At:</b> {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}",
            normal_style,
        )
    )

    duration = transcript.get("duration", "N/A")
    language = transcript.get("language", "N/A")

    story.append(
        Paragraph(f"<b>Duration:</b> {safe_text(duration)} seconds", normal_style)
    )
    story.append(Paragraph(f"<b>Language:</b> {safe_text(language)}", normal_style))
    story.append(Spacer(1, 12))

    speakers = transcript.get(
        "participants",
        transcript.get("speakers", []),
    )

    if not speakers:
        speakers = list(
            dict.fromkeys(
                segment.get("speaker")
                for segment in transcript.get("segments", [])
                if segment.get("speaker")
            )
        )

    story.append(Paragraph("Participants / Speakers", heading_style))

    if speakers:
        for speaker in speakers:
            story.append(Paragraph(f"• {safe_text(speaker)}", normal_style))
    else:
        story.append(Paragraph("No speaker labels available.", normal_style))

    story.append(Spacer(1, 10))

    story.append(Paragraph("Executive Summary", heading_style))
    story.append(
        Paragraph(
            safe_text(summary.get("short_summary", "No summary available.")),
            normal_style,
        )
    )

    story.append(Spacer(1, 10))

    story.append(Paragraph("Key Topics", heading_style))

    key_topics = summary.get("key_topics", [])

    if key_topics:
        for topic in key_topics:
            story.append(Paragraph(f"• {safe_text(topic)}", normal_style))
    else:
        story.append(Paragraph("No key topics detected.", normal_style))

    story.append(Spacer(1, 10))

    story.append(Paragraph("Action Items", heading_style))

    action_items = summary.get("action_items", [])

    if action_items:
        for index, item in enumerate(action_items, start=1):
            story.append(Paragraph(f"{index}. {safe_text(item)}", normal_style))
    else:
        story.append(Paragraph("No action items detected.", normal_style))

    story.append(Spacer(1, 10))

    story.append(Paragraph("Decisions", heading_style))

    decisions = summary.get("decisions", [])

    if decisions:
        for index, item in enumerate(decisions, start=1):
            story.append(Paragraph(f"{index}. {safe_text(item)}", normal_style))
    else:
        story.append(Paragraph("No decisions detected.", normal_style))

    story.append(Spacer(1, 12))

    story.append(Paragraph("Speaker-wise Transcript", heading_style))

    table_data = [["Time", "Speaker", "Text"]]

    for segment in transcript.get("segments", []):
        start = segment.get("start", 0)
        end = segment.get("end", 0)
        speaker = segment.get("speaker") or "Speaker"
        text = segment.get("text", "")

        table_data.append(
            [
                safe_text(f"{start}s - {end}s"),
                safe_text(speaker),
                Paragraph(safe_text(text), small_style),
            ]
        )

    if len(table_data) == 1:
        table_data.append(
            [
                "N/A",
                "N/A",
                Paragraph("No transcript segments found.", small_style),
            ]
        )

    table = Table(
        table_data,
        colWidths=[1.1 * inch, 1.2 * inch, 4.0 * inch],
        repeatRows=1,
    )

    table.setStyle(
        TableStyle(
            [
                ("BACKGROUND", (0, 0), (-1, 0), colors.HexColor("#2563eb")),
                ("TEXTCOLOR", (0, 0), (-1, 0), colors.white),
                ("FONTNAME", (0, 0), (-1, 0), "Helvetica-Bold"),
                ("FONTSIZE", (0, 0), (-1, -1), 8),
                ("GRID", (0, 0), (-1, -1), 0.4, colors.HexColor("#cbd5e1")),
                ("VALIGN", (0, 0), (-1, -1), "TOP"),
                ("BACKGROUND", (0, 1), (-1, -1), colors.HexColor("#f8fafc")),
            ]
        )
    )

    story.append(table)

    doc.build(story)

    return {
        "message": "Enhanced meeting minutes PDF generated successfully",
        "meeting_id": meeting_id,
        "pdf_filename": pdf_path.name,
        "pdf_path": str(pdf_path),
        "download_url": f"/api/pdf/download/{pdf_path.name}",
    }