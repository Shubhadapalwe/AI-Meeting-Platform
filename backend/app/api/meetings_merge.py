from fastapi import APIRouter, HTTPException

from app.services.meeting_aggregation_service import aggregate_meeting_transcripts

router = APIRouter()


@router.post("/aggregate/{meeting_id}")
def aggregate_meeting(meeting_id: str):
    try:
        return aggregate_meeting_transcripts(meeting_id)
    except FileNotFoundError as error:
        raise HTTPException(status_code=404, detail=str(error))
    except Exception as error:
        raise HTTPException(status_code=500, detail=str(error))