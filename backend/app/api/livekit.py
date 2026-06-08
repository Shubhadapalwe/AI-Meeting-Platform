from fastapi import APIRouter
from app.schemas.livekit import LiveKitTokenRequest, LiveKitTokenResponse
from app.services.livekit_service import LiveKitService

router = APIRouter()
service = LiveKitService()

@router.post("/token", response_model=LiveKitTokenResponse)
def create_livekit_token(payload: LiveKitTokenRequest):
    return service.create_room_token(
        room_name=payload.room_name,
        participant_name=payload.participant_name,
    )
