from typing import List
from fastapi import APIRouter
from app.schemas.participant import ParticipantEventRequest, ParticipantEventResponse
from app.services.participant_event_service import ParticipantEventService

router = APIRouter()
service = ParticipantEventService()

@router.post("/events", response_model=ParticipantEventResponse)
def record_participant_event(payload: ParticipantEventRequest):
    return service.record_event(payload)

@router.get("/events/{meeting_id}", response_model=List[ParticipantEventResponse])
def list_participant_events(meeting_id: str):
    return service.list_events(meeting_id)
