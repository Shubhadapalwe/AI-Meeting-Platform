from pydantic import BaseModel, Field
from typing import Optional
from datetime import datetime

class ParticipantEventRequest(BaseModel):
    meeting_id: str = Field(..., min_length=1)
    participant_name: str = Field(..., min_length=1)
    event_type: str = Field(..., min_length=1)
    is_muted: Optional[bool] = None
    is_camera_on: Optional[bool] = None
    is_screen_sharing: Optional[bool] = None
    speaker_score: Optional[float] = None

class ParticipantEventResponse(BaseModel):
    id: str
    meeting_id: str
    participant_name: str
    event_type: str
    is_muted: Optional[bool]
    is_camera_on: Optional[bool]
    is_screen_sharing: Optional[bool]
    speaker_score: Optional[float]
    created_at: datetime
