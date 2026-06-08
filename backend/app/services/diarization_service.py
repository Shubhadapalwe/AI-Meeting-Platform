"""
Phase 5 — Speaker Diarization

Strategy: We already record active_speaker events from LiveKit with wall-clock
timestamps. The recording starts at a known time (first event after joining).

Algorithm:
1. Load the transcript segments (already have start/end offsets in seconds).
2. Load active_speaker events for the meeting (wall-clock timestamps).
3. Compute a "recording start time" = earliest join event timestamp.
4. For each transcript segment, find which participant was speaking at that
   audio offset (segment.start seconds after recording start).
5. Assign that participant as the speaker label.

If no events exist, all segments get label "Speaker 1".
"""

import json
from pathlib import Path
from datetime import datetime, timezone, timedelta
from typing import List, Optional

BACKEND_ROOT = Path(__file__).resolve().parent.parent.parent
STORAGE_DIR = BACKEND_ROOT / "storage"
TRANSCRIPTS_DIR = STORAGE_DIR / "transcripts"
EVENTS_DIR = STORAGE_DIR / "events"


def _load_events(meeting_id: str) -> List[dict]:
    safe = meeting_id.replace("/", "_").replace(" ", "_")
    events_file = EVENTS_DIR / f"{safe}.json"
    if not events_file.exists():
        return []
    with open(events_file, "r", encoding="utf-8") as f:
        return json.load(f)


def _load_transcript(meeting_id: str) -> Optional[dict]:
    """Return the most recent transcript for this meeting."""
    candidates = list(TRANSCRIPTS_DIR.glob(f"{meeting_id}_*.json"))
    if not candidates:
        return None
    candidates.sort(key=lambda p: p.stat().st_mtime, reverse=True)
    with open(candidates[0], "r", encoding="utf-8") as f:
        return json.load(f), candidates[0]


def diarize(meeting_id: str) -> dict:
    result = _load_transcript(meeting_id)
    if result is None:
        raise FileNotFoundError(f"No transcript found for meeting {meeting_id}")

    transcript_data, transcript_path = result
    segments = transcript_data.get("segments", [])

    events = _load_events(meeting_id)
    speaker_events = [
        e for e in events if e.get("event_type") == "active_speaker"
    ]
    join_events = [
        e for e in events if e.get("event_type") == "joined"
    ]

    if not speaker_events:
        # No diarization data — label everything as Speaker 1
        for seg in segments:
            seg["speaker"] = "Speaker 1"
        transcript_data["segments"] = segments
        transcript_data["diarization_status"] = "no_events_available"
        _save_transcript(transcript_data, transcript_path)
        return transcript_data

    # Determine recording start time.
    # Priority: recording_started event > joined event > earliest speaker event.
    # "recording_started" is emitted by the frontend exactly when MediaRecorder.start()
    # is called, so its wall-clock time aligns with offset 0:00 in the audio file.
    recording_start_events = [
        e for e in events if e.get("event_type") == "recording_started"
    ]
    if recording_start_events:
        ref_events = recording_start_events
    elif join_events:
        ref_events = join_events
    else:
        ref_events = speaker_events

    recording_start = datetime.fromisoformat(
        min(e["created_at"] for e in ref_events).replace("Z", "+00:00")
    )

    # Build a sorted timeline of speaker activations
    timeline = []
    for e in sorted(speaker_events, key=lambda x: x["created_at"]):
        ts = datetime.fromisoformat(e["created_at"].replace("Z", "+00:00"))
        offset_seconds = (ts - recording_start).total_seconds()
        if offset_seconds < 0:
            offset_seconds = 0
        timeline.append({
            "participant": e["participant_name"],
            "offset": offset_seconds,
        })

    # Map each segment to a speaker
    for seg in segments:
        seg_mid = (seg["start"] + seg["end"]) / 2
        speaker = _find_speaker_at(timeline, seg_mid)
        seg["speaker"] = speaker

    # Build unique speaker list
    speakers = list(dict.fromkeys(
        s["speaker"] for s in segments if s.get("speaker")
    ))

    transcript_data["segments"] = segments
    transcript_data["speakers"] = speakers
    transcript_data["diarization_status"] = "completed"

    _save_transcript(transcript_data, transcript_path)
    return transcript_data


def _find_speaker_at(timeline: List[dict], offset: float) -> str:
    """Find the most recent speaker active at or before `offset` seconds."""
    best = None
    for entry in timeline:
        if entry["offset"] <= offset:
            best = entry["participant"]
        else:
            break
    return best or (timeline[0]["participant"] if timeline else "Unknown")


def _save_transcript(data: dict, path: Path):
    with open(path, "w", encoding="utf-8") as f:
        json.dump(data, f, indent=2, ensure_ascii=False)
