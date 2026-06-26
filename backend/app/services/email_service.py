"""
Email Digest Service — Fathom-style professional email format
"""

import os
import json
import smtplib
import email.utils
from email.mime.multipart import MIMEMultipart
from email.mime.text import MIMEText
from email.mime.application import MIMEApplication
from pathlib import Path
from datetime import datetime

BACKEND_ROOT  = Path(__file__).resolve().parent.parent.parent
STORAGE_DIR   = BACKEND_ROOT / "storage"
TRANSCRIPTS_DIR = STORAGE_DIR / "transcripts"
SUMMARIES_DIR = STORAGE_DIR / "summaries"
MEETINGS_FILE = STORAGE_DIR / "meetings.json"
PDF_DIR       = STORAGE_DIR / "pdfs"
EMAIL_LOG_DIR = STORAGE_DIR / "email_logs"
EMAIL_LOG_DIR.mkdir(parents=True, exist_ok=True)

SMTP_HOST     = os.getenv("SMTP_HOST", "")
SMTP_PORT     = int(os.getenv("SMTP_PORT", "587"))
SMTP_USER     = os.getenv("SMTP_USER", "")
SMTP_PASSWORD = os.getenv("SMTP_PASSWORD", "")
EMAIL_FROM    = os.getenv("EMAIL_FROM", SMTP_USER)
APP_BASE_URL  = os.getenv("APP_BASE_URL", "http://localhost:5173")


# ── Data loaders ──────────────────────────────────────────────────────────────

def _load_meeting(meeting_id: str) -> dict:
    if not MEETINGS_FILE.exists():
        return {}
    with open(MEETINGS_FILE, "r", encoding="utf-8") as f:
        data = json.load(f)
    return data.get(meeting_id, {})


def _load_summary(meeting_id: str) -> dict:
    files = list(SUMMARIES_DIR.glob(f"{meeting_id}*.json"))
    if not files:
        return {}
    files.sort(key=lambda p: p.stat().st_mtime, reverse=True)
    with open(files[0], "r", encoding="utf-8") as f:
        return json.load(f)


# ── HTML builder ──────────────────────────────────────────────────────────────

def _build_html(meeting_id: str, summary: dict, meeting: dict, pdf_url: str | None) -> str:
    title        = meeting.get("title") or "Meeting Summary"
    host         = meeting.get("host_name", "")
    created_raw  = summary.get("created_at", datetime.now().isoformat())
    try:
        dt = datetime.fromisoformat(created_raw)
        date_str = dt.strftime("%b %d, %Y  •  %I:%M %p")
    except Exception:
        date_str = created_raw[:16]

    purpose      = summary.get("meeting_purpose", summary.get("short_summary", ""))
    key_takeaways = summary.get("key_takeaways", [])
    topics       = summary.get("topics", [])
    action_items = summary.get("action_items", [])
    next_steps   = summary.get("next_steps", [])

    # ── Action items section ──────────────────────────────────────────────────
    if action_items:
        action_rows = "".join(
            f"""<tr>
                  <td style="padding:10px 0;border-bottom:1px solid #f1f5f9;color:#374151;font-size:14px;line-height:1.5">
                    <span style="color:#6366f1;font-weight:700;margin-right:8px">→</span>{item}
                  </td>
                </tr>"""
            for item in action_items
        )
        action_section = f"""
        <div style="margin-bottom:32px">
          <h2 style="font-size:13px;font-weight:700;text-transform:uppercase;letter-spacing:.08em;
                     color:#6366f1;margin:0 0 12px">✨ Action Items</h2>
          <table width="100%" cellpadding="0" cellspacing="0" style="border-top:1px solid #f1f5f9">
            {action_rows}
          </table>
        </div>"""
    else:
        action_section = """
        <div style="margin-bottom:32px">
          <h2 style="font-size:13px;font-weight:700;text-transform:uppercase;letter-spacing:.08em;
                     color:#6366f1;margin:0 0 12px">✨ Action Items</h2>
          <p style="color:#9ca3af;font-size:14px;margin:0">No action items detected in this meeting</p>
        </div>"""

    # ── Meeting Purpose ───────────────────────────────────────────────────────
    purpose_html = f"""
        <div style="margin-bottom:24px">
          <h3 style="font-size:12px;font-weight:700;text-transform:uppercase;letter-spacing:.08em;
                     color:#9ca3af;margin:0 0 8px">Meeting Purpose</h3>
          <p style="color:#374151;font-size:14px;line-height:1.6;margin:0">{purpose}</p>
        </div>""" if purpose else ""

    # ── Key Takeaways ─────────────────────────────────────────────────────────
    if key_takeaways:
        kt_rows = "".join(
            f"""<div style="margin-bottom:14px">
                  <span style="font-weight:700;color:#0f172a;font-size:14px">{kt.get('title','')}: </span>
                  <span style="color:#374151;font-size:14px;line-height:1.6">{kt.get('detail','')}</span>
                </div>"""
            for kt in key_takeaways if isinstance(kt, dict)
        )
        takeaways_section = f"""
        <div style="margin-bottom:24px">
          <h3 style="font-size:12px;font-weight:700;text-transform:uppercase;letter-spacing:.08em;
                     color:#9ca3af;margin:0 0 12px">Key Takeaways</h3>
          {kt_rows}
        </div>"""
    else:
        takeaways_section = ""

    # ── Topics ────────────────────────────────────────────────────────────────
    if topics:
        topic_blocks = ""
        for topic in topics:
            if not isinstance(topic, dict):
                continue
            points_html = "".join(
                f'<li style="color:#374151;font-size:13px;line-height:1.7;margin-bottom:2px">{p}</li>'
                for p in topic.get("points", [])
            )
            topic_blocks += f"""
            <div style="margin-bottom:20px">
              <div style="font-weight:700;color:#0f172a;font-size:14px;margin-bottom:6px">
                {topic.get('title','')}
              </div>
              <ul style="margin:0;padding-left:20px">{points_html}</ul>
            </div>"""
        topics_section = f"""
        <div style="margin-bottom:24px">
          <h3 style="font-size:12px;font-weight:700;text-transform:uppercase;letter-spacing:.08em;
                     color:#9ca3af;margin:0 0 12px">Topics</h3>
          {topic_blocks}
        </div>"""
    else:
        topics_section = ""

    # ── Next Steps ────────────────────────────────────────────────────────────
    if next_steps:
        ns_rows = "".join(
            f"""<tr>
                  <td style="padding:8px 12px 8px 0;font-weight:700;color:#0f172a;
                              font-size:13px;white-space:nowrap;vertical-align:top">
                    {ns.get('person','')}:
                  </td>
                  <td style="padding:8px 0;color:#374151;font-size:13px;line-height:1.5">
                    {ns.get('task','')}
                  </td>
                </tr>"""
            for ns in next_steps if isinstance(ns, dict)
        )
        next_steps_section = f"""
        <div style="margin-bottom:24px">
          <h3 style="font-size:12px;font-weight:700;text-transform:uppercase;letter-spacing:.08em;
                     color:#9ca3af;margin:0 0 12px">Next Steps</h3>
          <table cellpadding="0" cellspacing="0">{ns_rows}</table>
        </div>"""
    else:
        next_steps_section = ""

    # ── PDF button ────────────────────────────────────────────────────────────
    pdf_btn = ""
    if pdf_url:
        pdf_btn = f"""
        <div style="margin:28px 0 8px">
          <a href="{pdf_url}"
             style="display:inline-block;background:#0f172a;color:#fff;
                    padding:12px 24px;border-radius:8px;text-decoration:none;
                    font-weight:700;font-size:14px">
            📄 Download Meeting Minutes PDF
          </a>
        </div>"""

    return f"""<!DOCTYPE html>
<html lang="en">
<head><meta charset="utf-8"><meta name="viewport" content="width=device-width,initial-scale=1"></head>
<body style="margin:0;padding:0;background:#f8fafc;font-family:-apple-system,BlinkMacSystemFont,'Segoe UI',Roboto,sans-serif">

  <div style="max-width:640px;margin:32px auto;background:#fff;border-radius:12px;
              box-shadow:0 1px 3px rgba(0,0,0,.08),0 1px 2px rgba(0,0,0,.04);overflow:hidden">

    <!-- ── Top accent bar ── -->
    <div style="height:4px;background:linear-gradient(90deg,#6366f1,#8b5cf6)"></div>

    <!-- ── Header ── -->
    <div style="padding:28px 32px 20px;border-bottom:1px solid #f1f5f9">
      <div style="display:flex;align-items:center;justify-content:space-between;margin-bottom:12px">
        <span style="font-size:11px;font-weight:700;letter-spacing:.1em;text-transform:uppercase;color:#6366f1">
          AI Meeting Intelligence
        </span>
        <span style="font-size:11px;color:#9ca3af">Internal Meeting</span>
      </div>
      <h1 style="margin:0 0 6px;font-size:22px;font-weight:800;color:#0f172a;line-height:1.2">{title}</h1>
      <p style="margin:0;font-size:13px;color:#64748b">
        {date_str}{f"  •  Hosted by {host}" if host else ""}
      </p>
    </div>

    <!-- ── Body ── -->
    <div style="padding:28px 32px">

      {action_section}

      <!-- Meeting Summary header -->
      <h2 style="font-size:13px;font-weight:700;text-transform:uppercase;letter-spacing:.08em;
                 color:#6366f1;margin:0 0 20px">✨ Meeting Summary</h2>

      {purpose_html}
      {takeaways_section}
      {topics_section}
      {next_steps_section}

      {pdf_btn}

    </div>

    <!-- ── Footer ── -->
    <div style="padding:20px 32px;background:#f8fafc;border-top:1px solid #f1f5f9">
      <p style="margin:0;font-size:12px;color:#94a3b8;text-align:center">
        Sent by <strong>AI Meeting Intelligence Platform</strong> — Do not reply to this email.
      </p>
    </div>

  </div>
</body>
</html>"""


def _build_plain(meeting_id: str, summary: dict, meeting: dict) -> str:
    title   = meeting.get("title", "Meeting Summary")
    purpose = summary.get("meeting_purpose", summary.get("short_summary", ""))
    actions = "\n".join(f"  → {a}" for a in summary.get("action_items", [])) or "  None"
    kt      = "\n".join(
        f"  • {k.get('title','')}: {k.get('detail','')}"
        for k in summary.get("key_takeaways", []) if isinstance(k, dict)
    )
    ns      = "\n".join(
        f"  {n.get('person','')}: {n.get('task','')}"
        for n in summary.get("next_steps", []) if isinstance(n, dict)
    )
    return (
        f"{title}\n{'='*len(title)}\n\n"
        f"Meeting Purpose:\n{purpose}\n\n"
        f"Action Items:\n{actions}\n\n"
        + (f"Key Takeaways:\n{kt}\n\n" if kt else "")
        + (f"Next Steps:\n{ns}\n\n" if ns else "")
    )


# ── Public API ────────────────────────────────────────────────────────────────

def send_digest(
    meeting_id: str,
    recipient_emails: list[str],
    pdf_filename: str | None = None,
) -> dict:
    summary  = _load_summary(meeting_id)
    meeting  = _load_meeting(meeting_id)
    title    = meeting.get("title", "Meeting")
    pdf_url  = f"{APP_BASE_URL}/api/pdf/download/{pdf_filename}" if pdf_filename else None

    html_body  = _build_html(meeting_id, summary, meeting, pdf_url)
    plain_body = _build_plain(meeting_id, summary, meeting)
    subject    = f"Meeting Summary: {title}"

    sent_to = []
    failed  = []

    log_data = {
        "meeting_id": meeting_id,
        "sent_at": datetime.now().isoformat(timespec="seconds"),
        "recipients": recipient_emails,
        "subject": subject,
        "plain_body": plain_body,
        "smtp_configured": bool(SMTP_HOST and SMTP_USER),
    }
    log_path = EMAIL_LOG_DIR / f"{meeting_id}_{datetime.now().strftime('%Y%m%d_%H%M%S')}.json"
    with open(log_path, "w", encoding="utf-8") as f:
        json.dump(log_data, f, indent=2, ensure_ascii=False)

    if not SMTP_HOST or not SMTP_USER:
        return {
            "status": "dry_run",
            "message": "SMTP not configured. Email saved to log.",
            "recipients": recipient_emails,
            "log_path": str(log_path),
        }

    try:
        with smtplib.SMTP(SMTP_HOST, SMTP_PORT) as server:
            server.ehlo()
            server.starttls()
            server.login(SMTP_USER, SMTP_PASSWORD)

            pdf_bytes = None
            if pdf_filename:
                pdf_path = PDF_DIR / pdf_filename
                if pdf_path.exists():
                    pdf_bytes = pdf_path.read_bytes()

            for recipient in recipient_emails:
                try:
                    msg = MIMEMultipart("mixed")
                    msg["Subject"] = subject
                    msg["From"]    = EMAIL_FROM or SMTP_USER
                    msg["To"]      = recipient
                    msg["Date"]    = email.utils.formatdate(localtime=True)

                    alt = MIMEMultipart("alternative")
                    alt.attach(MIMEText(plain_body, "plain"))
                    alt.attach(MIMEText(html_body, "html"))
                    msg.attach(alt)

                    if pdf_bytes:
                        pdf_part = MIMEApplication(pdf_bytes, Name=pdf_filename)
                        pdf_part["Content-Disposition"] = f'attachment; filename="{pdf_filename}"'
                        msg.attach(pdf_part)

                    server.sendmail(SMTP_USER, recipient, msg.as_string())
                    sent_to.append(recipient)
                except Exception as e:
                    failed.append({"email": recipient, "error": str(e)})

    except Exception as e:
        return {
            "status": "smtp_error",
            "message": str(e),
            "recipients": recipient_emails,
            "sent": sent_to,
            "failed": failed,
            "log_path": str(log_path),
        }

    return {
        "status": "sent" if not failed else "partial",
        "message": f"Sent to {len(sent_to)} recipient(s).",
        "sent": sent_to,
        "failed": failed,
        "log_path": str(log_path),
    }
