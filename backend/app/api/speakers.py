"""
Phase 9 — Speaker Analytics API

Provides per-speaker statistics for a meeting:
- speaking time, word count, segment count, speaking percentage
- timeline of when each speaker was active
- top keywords per speaker
"""

from fastapi import APIRouter, HTTPException
from pathlib import Path
from collections import Counter
import json
import re

router = APIRouter()

BACKEND_ROOT = Path(__file__).resolve().parent.parent.parent
STORAGE_DIR = BACKEND_ROOT / "storage"
TRANSCRIPTS_DIR = STORAGE_DIR / "transcripts"
MEETINGS_DIR = STORAGE_DIR / "meetings"

STOP_WORDS = {
    "the", "a", "an", "and", "or", "but", "in", "on", "at", "to", "for",
    "of", "with", "by", "from", "is", "are", "was", "were", "be", "been",
    "have", "has", "had", "do", "does", "did", "will", "would", "could",
    "should", "may", "might", "that", "this", "it", "i", "you", "we",
    "he", "she", "they", "so", "as", "if", "not", "just", "yeah", "okay",
    "yes", "no", "like", "think", "know", "get", "got", "um", "uh",
}


def _load_merged_transcript(meeting_id: str):
    """Load merged transcript, falling back to latest individual transcript."""
    # Try merged first (produced by diarize or aggregate)
    merged = MEETINGS_DIR / f"{meeting_id}_merged.json"
    if merged.exists():
        with open(merged, "r", encoding="utf-8") as f:
            return json.load(f)

    merged_t = TRANSCRIPTS_DIR / f"{meeting_id}_merged.json"
    if merged_t.exists():
        with open(merged_t, "r", encoding="utf-8") as f:
            return json.load(f)

    # Fall back to most recent transcript file for this meeting
    files = sorted(
        TRANSCRIPTS_DIR.glob(f"{meeting_id}_*.json"),
        key=lambda p: p.stat().st_mtime,
        reverse=True,
    )
    if not files:
        return None
    with open(files[0], "r", encoding="utf-8") as f:
        return json.load(f)


def _top_keywords(text: str, n: int = 8):
    words = re.findall(r"\b[a-zA-Z]{4,}\b", text.lower())
    filtered = [w for w in words if w not in STOP_WORDS]
    return [word for word, _ in Counter(filtered).most_common(n)]


def _build_analytics(segments: list, total_duration: float):
    speakers: dict = {}

    for seg in segments:
        speaker = seg.get("speaker") or "Unknown"
        start = float(seg.get("start", 0) or 0)
        end = float(seg.get("end", start) or start)
        text = seg.get("text", "").strip()
        duration = max(end - start, 0)
        words = len(text.split()) if text else 0

        if speaker not in speakers:
            speakers[speaker] = {
                "speaker": speaker,
                "speaking_time_seconds": 0.0,
                "word_count": 0,
                "segment_count": 0,
                "text_parts": [],
                "timeline": [],
            }

        speakers[speaker]["speaking_time_seconds"] += duration
        speakers[speaker]["word_count"] += words
        speakers[speaker]["segment_count"] += 1
        speakers[speaker]["text_parts"].append(text)
        speakers[speaker]["timeline"].append({"start": start, "end": end})

    total_speaking = sum(s["speaking_time_seconds"] for s in speakers.values())
    ref_duration = total_duration if total_duration > 0 else total_speaking

    result = []
    for data in speakers.values():
        speaking_time = round(data["speaking_time_seconds"], 1)
        pct = round((speaking_time / ref_duration * 100), 1) if ref_duration > 0 else 0.0
        combined_text = " ".join(data["text_parts"])
        result.append({
            "speaker": data["speaker"],
            "speaking_time_seconds": speaking_time,
            "speaking_percentage": pct,
            "word_count": data["word_count"],
            "segment_count": data["segment_count"],
            "words_per_minute": round(
                data["word_count"] / (speaking_time / 60), 1
            ) if speaking_time > 0 else 0,
            "top_keywords": _top_keywords(combined_text),
            "timeline": data["timeline"],
        })

    result.sort(key=lambda x: x["speaking_time_seconds"], reverse=True)
    return result


@router.get("/{meeting_id}")
def get_speaker_analytics(meeting_id: str):
    """Return per-speaker analytics for a meeting."""
    transcript = _load_merged_transcript(meeting_id)
    if not transcript:
        raise HTTPException(
            status_code=404,
            detail="No transcript found. Generate and diarize transcript first.",
        )

    segments = transcript.get("segments", [])
    duration = float(transcript.get("duration", 0) or 0)

    analytics = _build_analytics(segments, duration)

    return {
        "meeting_id": meeting_id,
        "duration_seconds": duration,
        "participant_count": len(analytics),
        "analytics": analytics,
    }


@router.get("/{meeting_id}/timeline")
def get_speaker_timeline(meeting_id: str):
    """Return a flat timeline of who spoke when — useful for rendering a waveform view."""
    transcript = _load_merged_transcript(meeting_id)
    if not transcript:
        raise HTTPException(status_code=404, detail="No transcript found.")

    timeline = []
    for seg in transcript.get("segments", []):
        speaker = seg.get("speaker") or "Unknown"
        start = float(seg.get("start", 0) or 0)
        end = float(seg.get("end", start) or start)
        text = seg.get("text", "").strip()
        if text:
            timeline.append({
                "speaker": speaker,
                "start": round(start, 2),
                "end": round(end, 2),
                "text": text,
            })

    timeline.sort(key=lambda x: x["start"])

    return {
        "meeting_id": meeting_id,
        "segment_count": len(timeline),
        "timeline": timeline,
    }
