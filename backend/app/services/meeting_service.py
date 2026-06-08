import json
from uuid import uuid4
from pathlib import Path
from app.schemas.meeting import MeetingResponse
from app.core.config import settings

BACKEND_ROOT = Path(__file__).resolve().parent.parent.parent
MEETINGS_FILE = BACKEND_ROOT / "storage" / "meetings.json"
MEETINGS_FILE.parent.mkdir(parents=True, exist_ok=True)


class MeetingService:
    def __init__(self):
        self.meetings: dict = {}
        self._load()

    def _load(self):
        if MEETINGS_FILE.exists():
            try:
                with open(MEETINGS_FILE, "r", encoding="utf-8") as f:
                    raw = json.load(f)
                self.meetings = {k: MeetingResponse(**v) for k, v in raw.items()}
            except Exception:
                self.meetings = {}

    def _save(self):
        with open(MEETINGS_FILE, "w", encoding="utf-8") as f:
            json.dump(
                {k: v.model_dump() for k, v in self.meetings.items()},
                f,
                indent=2,
                default=str,
            )

    def create_meeting(self, title: str, host_name: str) -> MeetingResponse:
        meeting_id = str(uuid4())[:8]
        meeting = MeetingResponse(
            meeting_id=meeting_id,
            title=title,
            host_name=host_name,
            join_url=f"{settings.APP_BASE_URL}/meeting/{meeting_id}",
            status="created",
        )
        self.meetings[meeting_id] = meeting
        self._save()
        return meeting

    def get_meeting(self, meeting_id: str):
        return self.meetings.get(meeting_id)

    def list_meetings(self):
        return list(self.meetings.values())
