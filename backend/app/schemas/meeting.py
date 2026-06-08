from pydantic import BaseModel, Field

class CreateMeetingRequest(BaseModel):
    title: str = Field(default="Untitled Meeting", min_length=1)
    host_name: str = Field(default="Host", min_length=1)

class MeetingResponse(BaseModel):
    meeting_id: str
    title: str
    host_name: str
    join_url: str
    status: str
