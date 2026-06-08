from pydantic import BaseModel, Field

class LiveKitTokenRequest(BaseModel):
    room_name: str = Field(..., min_length=1)
    participant_name: str = Field(..., min_length=1)

class LiveKitTokenResponse(BaseModel):
    url: str
    token: str
    room_name: str
    participant_name: str
