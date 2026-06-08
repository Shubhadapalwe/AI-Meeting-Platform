from fastapi import APIRouter, HTTPException, Query
from pathlib import Path
import json, re
from app.schemas.meeting import CreateMeetingRequest, MeetingResponse
from app.services.meeting_service import MeetingService

router = APIRouter()
service = MeetingService()

BACKEND_ROOT = Path(__file__).resolve().parent.parent.parent
TRANSCRIPTS_DIR = BACKEND_ROOT / "storage" / "transcripts"


@router.post("/create", response_model=MeetingResponse)
def create_meeting(payload: CreateMeetingRequest):
    meeting = service.create_meeting(title=payload.title, host_name=payload.host_name)
    return meeting


@router.get("/history")
def list_meetings():
    """Phase 8 — list all meetings with basic metadata."""
    meetings = service.list_meetings()
    result = []
    for m in meetings:
        data = m.model_dump()
        # Enrich with transcript info if available
        t_files = list(TRANSCRIPTS_DIR.glob(f"{m.meeting_id}_*.json"))
        if t_files:
            t_files.sort(key=lambda p: p.stat().st_mtime, reverse=True)
            with open(t_files[0], "r", encoding="utf-8") as f:
                t = json.load(f)
            data["has_transcript"] = True
            data["transcript_duration"] = t.get("duration", 0)
            data["transcript_words"] = len(t.get("full_text", "").split())
        else:
            data["has_transcript"] = False
        result.append(data)
    result.sort(key=lambda x: x.get("created_at", ""), reverse=True)
    return {"meetings": result, "total": len(result)}


@router.get("/search")
def search_transcripts(q: str = Query(..., min_length=1)):
    """Phase 8 — full-text search across all transcript files."""
    q_lower = q.lower()
    results = []
    for t_file in TRANSCRIPTS_DIR.glob("*.json"):
        with open(t_file, "r", encoding="utf-8") as f:
            data = json.load(f)
        full_text = data.get("full_text", "")
        if q_lower not in full_text.lower():
            continue
        # Find matching segments
        matching_segments = [
            s for s in data.get("segments", [])
            if q_lower in s.get("text", "").lower()
        ]
        results.append({
            "meeting_id": data.get("meeting_id"),
            "transcript_id": data.get("transcript_id"),
            "created_at": data.get("created_at"),
            "matching_segments": matching_segments[:5],
            "total_matches": len(matching_segments),
        })
    return {"query": q, "results": results, "total": len(results)}


@router.get("/{meeting_id}", response_model=MeetingResponse)
def get_meeting(meeting_id: str):
    meeting = service.get_meeting(meeting_id)
    if not meeting:
        raise HTTPException(status_code=404, detail="Meeting not found")
    return meeting
