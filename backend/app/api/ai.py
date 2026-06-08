from fastapi import APIRouter, HTTPException
from app.schemas.ai import (
    MockSummaryRequest,
    MockSummaryResponse,
    SummaryRequest,
    SummaryResponse,
    AskAIRequest,
    AskAIResponse,
)
from app.services.ai_service import AIService
from app.services.ask_ai_service import answer_question
router = APIRouter()
service = AIService()


# Phase 2 legacy — kept for backward compat
@router.post("/mock-summary", response_model=MockSummaryResponse)
def mock_summary(payload: MockSummaryRequest):
    return service.generate_mock_summary(payload.transcript)


# Phase 6 — Real AI Summary
@router.post("/summary", response_model=SummaryResponse)
def generate_summary(payload: SummaryRequest):
    try:
        return service.generate_summary(payload.meeting_id)
    except FileNotFoundError as e:
        raise HTTPException(status_code=404, detail=str(e))
    except Exception as e:
        msg = str(e)
        # Hide raw connection errors (Ollama not running, etc.)
        if "HTTPConnection" in msg or "Connection refused" in msg or "11434" in msg:
            raise HTTPException(status_code=500, detail="AI model unavailable. Generate a transcript first.")
        raise HTTPException(status_code=500, detail=msg)


# Phase 7 — Ask AI
@router.post("/ask")
def ask_ai(payload: dict):
    try:
        meeting_id = payload.get("meeting_id")
        question = payload.get("question")

        if not meeting_id or not question:
            raise HTTPException(
                status_code=400,
                detail="meeting_id and question are required",
            )

        result = answer_question(meeting_id, question)

        return {
            "meeting_id": meeting_id,
            "question": question,
            "answer": result["answer"],
            "source": result["source"],
        }

    except FileNotFoundError as error:
        raise HTTPException(status_code=404, detail=str(error))

    except ValueError as error:
        raise HTTPException(status_code=400, detail=str(error))

    except Exception as error:
        msg = str(error)
        if "HTTPConnection" in msg or "Connection refused" in msg or "11434" in msg:
            raise HTTPException(status_code=500, detail="AI model unavailable.")
        raise HTTPException(status_code=500, detail=msg)

# Phase 8 — Analytics
@router.get("/analytics/{meeting_id}")
def get_analytics(meeting_id: str):
    try:
        return service.get_analytics(meeting_id)
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))
