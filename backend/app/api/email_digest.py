"""
Phase 10 — Email Digest API

POST /api/email/send/{meeting_id}
  Body: { "emails": ["a@b.com", "c@d.com"], "pdf_filename": "meeting_minutes_xxx.pdf" }

GET  /api/email/logs/{meeting_id}
  Returns list of digest emails sent for this meeting.
"""

from fastapi import APIRouter, HTTPException
from pydantic import BaseModel, EmailStr
from pathlib import Path
from typing import List, Optional
import json

from app.services.email_service import send_digest, EMAIL_LOG_DIR

router = APIRouter()


class DigestRequest(BaseModel):
    emails: List[EmailStr]
    pdf_filename: Optional[str] = None


@router.post("/send/{meeting_id}")
def send_meeting_digest(meeting_id: str, payload: DigestRequest):
    """
    Send (or dry-run log) the AI meeting summary digest to the given email addresses.
    Works without SMTP configuration — saves email content to storage/email_logs/.
    """
    if not payload.emails:
        raise HTTPException(status_code=400, detail="At least one email address is required.")

    try:
        result = send_digest(
            meeting_id=meeting_id,
            recipient_emails=payload.emails,
            pdf_filename=payload.pdf_filename,
        )
        # SMTP errors come back as a dict with status="smtp_error" — raise so
        # the frontend receives a proper HTTP error, not a false 200 success.
        if result.get("status") == "smtp_error":
            raise HTTPException(status_code=502, detail=result.get("message", "SMTP error"))
        return result
    except HTTPException:
        raise
    except FileNotFoundError as e:
        raise HTTPException(status_code=404, detail=str(e))
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/logs/{meeting_id}")
def get_digest_logs(meeting_id: str):
    """Return all digest email logs for this meeting."""
    logs = []
    for log_file in sorted(EMAIL_LOG_DIR.glob(f"{meeting_id}_*.json"), reverse=True):
        try:
            with open(log_file, "r", encoding="utf-8") as f:
                logs.append(json.load(f))
        except Exception:
            continue
    return {"meeting_id": meeting_id, "total": len(logs), "logs": logs}
