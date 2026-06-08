from datetime import datetime, timedelta, timezone
from uuid import uuid4
import jwt
from app.core.config import settings
from app.schemas.livekit import LiveKitTokenResponse

class LiveKitService:
    """Creates LiveKit-compatible JWT room tokens.

    We generate the token ourselves instead of forcing a heavy SDK dependency.
    LiveKit accepts JWT tokens with `video` grants such as roomJoin, room,
    canPublish and canSubscribe.
    """

    def create_room_token(self, room_name: str, participant_name: str) -> LiveKitTokenResponse:
        now = datetime.now(timezone.utc)
        expires_at = now + timedelta(seconds=settings.LIVEKIT_TOKEN_TTL_SECONDS)

        claims = {
            "iss": settings.LIVEKIT_API_KEY,
            "sub": f"{participant_name}-{uuid4().hex[:8]}",
            "name": participant_name,
            "nbf": int(now.timestamp()),
            "exp": int(expires_at.timestamp()),
            "jti": uuid4().hex,
            "video": {
                "roomJoin": True,
                "room": room_name,
                "canPublish": True,
                "canSubscribe": True,
                "canPublishData": True,
            },
        }

        token = jwt.encode(claims, settings.LIVEKIT_API_SECRET, algorithm="HS256")
        return LiveKitTokenResponse(
            url=settings.LIVEKIT_PUBLIC_URL,  # browser-reachable URL, not Docker-internal
            token=token,
            room_name=room_name,
            participant_name=participant_name,
        )
