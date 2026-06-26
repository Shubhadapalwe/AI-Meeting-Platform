from pydantic import BaseModel
from typing import List, Optional, Any


class MockSummaryRequest(BaseModel):
    transcript: str


class MockSummaryResponse(BaseModel):
    short_summary: str
    action_items: List[str]
    decisions: List[str]


# Phase 6 — Real summary
class SummaryRequest(BaseModel):
    meeting_id: str


class SummaryResponse(BaseModel):
    short_summary: str
    action_items: List[str]
    decisions: List[str]
    key_topics: List[str] = []
    word_count: int = 0
    generated_by: str = "extractive_fallback"
    # Fathom-style rich fields
    meeting_purpose: str = ""
    key_takeaways: List[Any] = []   # [{"title": str, "detail": str}]
    topics: List[Any] = []          # [{"title": str, "points": [str]}]
    next_steps: List[Any] = []      # [{"person": str, "task": str}]


# Phase 7 — Ask AI
class AskAIRequest(BaseModel):
    meeting_id: str
    question: str


class AskAIResponse(BaseModel):
    meeting_id: str
    question: str
    answer: str
    generated_by: str = "keyword_search"
