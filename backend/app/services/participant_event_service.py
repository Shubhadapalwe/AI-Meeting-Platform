import json
from uuid import uuid4
from datetime import datetime, timezone
from typing import List
from pathlib import Path
from app.schemas.participant import ParticipantEventRequest, ParticipantEventResponse

BACKEND_ROOT = Path(__file__).resolve().parent.parent.parent
EVENTS_DIR = BACKEND_ROOT / "storage" / "events"
EVENTS_DIR.mkdir(parents=True, exist_ok=True)


class ParticipantEventService:
    def __init__(self):
        self.events: List[ParticipantEventResponse] = []
        self._load_all()

    def _events_file(self, meeting_id: str) -> Path:
        safe = meeting_id.replace("/", "_").replace(" ", "_")
        return EVENTS_DIR / f"{safe}.json"

    def _load_all(self):
        for f in EVENTS_DIR.glob("*.json"):
            try:
                with open(f, "r", encoding="utf-8") as fp:
                    for item in json.load(fp):
                        self.events.append(ParticipantEventResponse(**item))
            except Exception:
                pass

    def _save_meeting_events(self, meeting_id: str):
        evts = [e for e in self.events if e.meeting_id == meeting_id]
        with open(self._events_file(meeting_id), "w", encoding="utf-8") as f:
            json.dump([e.model_dump() for e in evts], f, indent=2, default=str)

    def record_event(self, payload: ParticipantEventRequest) -> ParticipantEventResponse:
        event = ParticipantEventResponse(
            id=uuid4().hex,
            meeting_id=payload.meeting_id,
            participant_name=payload.participant_name,
            event_type=payload.event_type,
            is_muted=payload.is_muted,
            is_camera_on=payload.is_camera_on,
            is_screen_sharing=payload.is_screen_sharing,
            speaker_score=payload.speaker_score,
            created_at=datetime.now(timezone.utc),
        )
        self.events.append(event)
        self._save_meeting_events(payload.meeting_id)
        return event

    def list_events(self, meeting_id: str) -> List[ParticipantEventResponse]:
        return [e for e in self.events if e.meeting_id == meeting_id]

    def get_active_speaker_timeline(self, meeting_id: str) -> List[dict]:
        """Return sorted list of {participant_name, timestamp} for active_speaker events."""
        evts = [
            e for e in self.events
            if e.meeting_id == meeting_id and e.event_type == "active_speaker"
        ]
        evts.sort(key=lambda e: e.created_at)
        return [
            {"participant_name": e.participant_name, "timestamp": e.created_at.isoformat()}
            for e in evts
        ]
