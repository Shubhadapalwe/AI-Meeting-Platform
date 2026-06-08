"""
Phase 6 — AI Summary Service

Uses OpenAI GPT-4o-mini if OPENAI_API_KEY is set, otherwise falls back to
a local extractive summary so the system works without an API key.
"""

import os
import re
import json
from pathlib import Path
from typing import List, Optional
from app.schemas.ai import (
    MockSummaryRequest,
    MockSummaryResponse,
    SummaryRequest,
    SummaryResponse,
    AskAIRequest,
    AskAIResponse,
)

BACKEND_ROOT = Path(__file__).resolve().parent.parent.parent
STORAGE_DIR = BACKEND_ROOT / "storage"
TRANSCRIPTS_DIR = STORAGE_DIR / "transcripts"

OPENAI_API_KEY = os.getenv("OPENAI_API_KEY", "")


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _get_openai_client():
    if not OPENAI_API_KEY:
        return None
    try:
        from openai import OpenAI
        return OpenAI(api_key=OPENAI_API_KEY)
    except ImportError:
        return None


def _load_transcript_text(meeting_id: str) -> Optional[str]:
    candidates = list(TRANSCRIPTS_DIR.glob(f"{meeting_id}_*.json"))
    if not candidates:
        return None
    candidates.sort(key=lambda p: p.stat().st_mtime, reverse=True)
    with open(candidates[0], "r", encoding="utf-8") as f:
        data = json.load(f)
    return data.get("full_text") or " ".join(
        s.get("text", "") for s in data.get("segments", [])
    )


def _load_transcript_with_speakers(meeting_id: str) -> Optional[str]:
    """Return transcript text with speaker labels, suitable for LLM input."""
    candidates = list(TRANSCRIPTS_DIR.glob(f"{meeting_id}_*.json"))
    if not candidates:
        return None
    candidates.sort(key=lambda p: p.stat().st_mtime, reverse=True)
    with open(candidates[0], "r", encoding="utf-8") as f:
        data = json.load(f)

    segments = data.get("segments", [])
    if not segments:
        return data.get("full_text", "")

    lines = []
    current_speaker = None
    for seg in segments:
        speaker = seg.get("speaker") or "Speaker"
        text = seg.get("text", "").strip()
        if not text:
            continue
        if speaker != current_speaker:
            current_speaker = speaker
            lines.append(f"\n{speaker}: {text}")
        else:
            lines.append(text)
    return " ".join(lines).strip()


# ---------------------------------------------------------------------------
# Extractive fallback (no API key needed)
# ---------------------------------------------------------------------------

def _extractive_summary(text: str) -> SummaryResponse:
    words = text.split()
    word_count = len(words)

    # Short summary: first ~50 words
    short = " ".join(words[:50])
    if len(words) > 50:
        short += "..."

    sentences = re.split(r"(?<=[.!?])\s+", text)

    # Action items: sentences containing action keywords
    action_keywords = ["will", "should", "need to", "must", "going to", "action", "task", "todo", "follow up"]
    action_items = [
        s.strip() for s in sentences
        if any(kw in s.lower() for kw in action_keywords)
    ][:5]

    # Decisions: sentences containing decision keywords
    decision_keywords = ["decided", "agreed", "confirmed", "resolved", "approved", "chosen", "selected"]
    decisions = [
        s.strip() for s in sentences
        if any(kw in s.lower() for kw in decision_keywords)
    ][:5]

    if not action_items:
        action_items = ["Review the meeting notes and follow up on discussed topics."]
    if not decisions:
        decisions = ["No explicit decisions detected — review the full transcript."]

    return SummaryResponse(
        short_summary=short,
        action_items=action_items,
        decisions=decisions,
        word_count=word_count,
        generated_by="extractive_fallback",
    )


# ---------------------------------------------------------------------------
# OpenAI-powered summary
# ---------------------------------------------------------------------------

def _openai_summary(text: str) -> SummaryResponse:
    client = _get_openai_client()
    if not client:
        return _extractive_summary(text)

    prompt = f"""You are an AI meeting assistant. Analyze the following meeting transcript and return a JSON object with these keys:
- short_summary: 2-3 sentence summary of the meeting
- action_items: list of action items (strings), what needs to be done
- decisions: list of key decisions made (strings)

Transcript:
{text[:8000]}

Respond with valid JSON only."""

    try:
        response = client.chat.completions.create(
            model="gpt-4o-mini",
            messages=[{"role": "user", "content": prompt}],
            temperature=0.3,
        )
        raw = response.choices[0].message.content.strip()
        # Strip markdown code block if present
        raw = re.sub(r"^```(?:json)?\s*", "", raw)
        raw = re.sub(r"\s*```$", "", raw)
        data = json.loads(raw)
        return SummaryResponse(
            short_summary=data.get("short_summary", ""),
            action_items=data.get("action_items", []),
            decisions=data.get("decisions", []),
            word_count=len(text.split()),
            generated_by="gpt-4o-mini",
        )
    except Exception as e:
        # Fall back to extractive on any error
        result = _extractive_summary(text)
        result.short_summary = f"[OpenAI error: {e}] " + result.short_summary
        return result


# ---------------------------------------------------------------------------
# Ask AI
# ---------------------------------------------------------------------------

def _ask_openai(question: str, transcript: str) -> str:
    client = _get_openai_client()
    if not client:
        return _keyword_search(question, transcript)

    prompt = f"""You are an AI meeting assistant. Answer the user's question based only on the transcript below.
If the answer is not in the transcript, say "I couldn't find that in the transcript."

Transcript:
{transcript[:8000]}

Question: {question}

Answer:"""
    try:
        response = client.chat.completions.create(
            model="gpt-4o-mini",
            messages=[{"role": "user", "content": prompt}],
            temperature=0.2,
        )
        return response.choices[0].message.content.strip()
    except Exception as e:
        return _keyword_search(question, transcript)


def _keyword_search(question: str, transcript: str) -> str:
    """Simple keyword matching fallback."""
    keywords = [
        w.lower().strip("?.,!")
        for w in question.split()
        if len(w) > 3
    ]
    sentences = re.split(r"(?<=[.!?])\s+", transcript)
    matches = []
    for sentence in sentences:
        sl = sentence.lower()
        if sum(1 for kw in keywords if kw in sl) >= max(1, len(keywords) // 3):
            matches.append(sentence.strip())
    if matches:
        return " ... ".join(matches[:4])
    return "No matching content found in the transcript for your question."


# ---------------------------------------------------------------------------
# Public service class
# ---------------------------------------------------------------------------

class AIService:
    def generate_mock_summary(self, transcript: str) -> MockSummaryResponse:
        """Legacy mock endpoint — kept for backward compatibility."""
        text = transcript.strip()
        short = "This meeting discussed project planning, technical modules, and next implementation steps."
        if text:
            short = f"Mock summary generated from {len(text.split())} transcript words."
        return MockSummaryResponse(
            short_summary=short,
            action_items=[
                "Prepare authentication module.",
                "Connect meeting room with LiveKit/WebRTC.",
                "Add recording and transcription pipeline.",
            ],
            decisions=[
                "Build custom meeting platform instead of depending fully on Zoom integration.",
                "Separate meeting infrastructure layer and AI intelligence layer.",
            ],
        )

    def generate_summary(self, meeting_id: str) -> SummaryResponse:
        from datetime import datetime
        text = _load_transcript_with_speakers(meeting_id)
        if not text:
            raise FileNotFoundError(f"No transcript found for meeting {meeting_id}")
        result = _openai_summary(text) if OPENAI_API_KEY else _extractive_summary(text)

        # Save to disk so PDF generation can find it without calling Ollama
        summaries_dir = STORAGE_DIR / "summaries"
        summaries_dir.mkdir(parents=True, exist_ok=True)
        summary_path = summaries_dir / f"{meeting_id}_summary.json"
        with open(summary_path, "w", encoding="utf-8") as f:
            json.dump({
                "meeting_id": meeting_id,
                "short_summary": result.short_summary,
                "key_topics": result.key_topics,
                "action_items": result.action_items,
                "decisions": result.decisions,
                "generated_by": result.generated_by,
                "word_count": result.word_count,
                "created_at": datetime.now().isoformat(timespec="seconds"),
            }, f, indent=2, ensure_ascii=False)

        return result

    def ask(self, meeting_id: str, question: str) -> AskAIResponse:
        text = _load_transcript_with_speakers(meeting_id)
        if not text:
            raise FileNotFoundError(f"No transcript found for meeting {meeting_id}")
        answer = _ask_openai(question, text)
        return AskAIResponse(
            meeting_id=meeting_id,
            question=question,
            answer=answer,
            generated_by="gpt-4o-mini" if OPENAI_API_KEY else "keyword_search",
        )

    def get_analytics(self, meeting_id: str) -> dict:
        """Phase 8 — meeting analytics."""
        candidates = list(TRANSCRIPTS_DIR.glob(f"{meeting_id}_*.json"))
        if not candidates:
            return {"meeting_id": meeting_id, "error": "No transcript found"}

        candidates.sort(key=lambda p: p.stat().st_mtime, reverse=True)
        with open(candidates[0], "r", encoding="utf-8") as f:
            data = json.load(f)

        segments = data.get("segments", [])
        full_text = data.get("full_text", "")
        speakers_set = {}

        for seg in segments:
            sp = seg.get("speaker") or "Unknown"
            if sp not in speakers_set:
                speakers_set[sp] = {"word_count": 0, "segment_count": 0}
            words = len(seg.get("text", "").split())
            speakers_set[sp]["word_count"] += words
            speakers_set[sp]["segment_count"] += 1

        return {
            "meeting_id": meeting_id,
            "duration_seconds": data.get("duration", 0),
            "language": data.get("language", "unknown"),
            "total_words": len(full_text.split()),
            "total_segments": len(segments),
            "speakers": speakers_set,
            "created_at": data.get("created_at"),
        }
