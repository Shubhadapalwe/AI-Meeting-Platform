"""
Phase 2 — Speaker Identification (simplified)

Since each audio file is recorded by exactly one participant, speaker labels
are assigned at transcription time from the recording metadata. This service
just merges all per-participant transcripts, deduplicates, and sorts by time.
LiveKit active_speaker events are no longer needed for speaker assignment.
"""

import json
from pathlib import Path
from datetime import datetime

BACKEND_ROOT = Path(__file__).resolve().parent.parent.parent
STORAGE_DIR = BACKEND_ROOT / "storage"
TRANSCRIPTS_DIR = STORAGE_DIR / "transcripts"


def diarize(meeting_id: str) -> dict:
    """Merge all transcripts for this meeting into one sorted transcript."""

    # Exclude previously-written merged file so it doesn't pollute the next run
    # (merged.json matches the glob but contains stale combined data from last run)
    transcript_files = sorted(
        [
            p for p in TRANSCRIPTS_DIR.glob(f"{meeting_id}_*.json")
            if not p.name.endswith("_merged.json")
        ],
        key=lambda p: p.stat().st_mtime,
    )
    if not transcript_files:
        raise FileNotFoundError(
            f"No transcripts found for meeting {meeting_id}. "
            "Generate transcript first."
        )

    merged_segments = []
    participants = set()
    language = "unknown"
    max_duration = 0.0

    for tf in transcript_files:
        try:
            with open(tf, "r", encoding="utf-8") as f:
                data = json.load(f)
        except Exception:
            continue

        language = data.get("language", language)
        max_duration = max(max_duration, float(data.get("duration", 0) or 0))

        for seg in data.get("segments", []):
            seg = dict(seg)
            speaker = seg.get("speaker") or data.get("participant_name") or "Speaker"
            seg["speaker"] = speaker
            participants.add(speaker)
            merged_segments.append(seg)

    # Deduplicate by (start, end, text)
    seen = set()
    deduped = []
    for seg in merged_segments:
        key = (
            round(float(seg.get("start", 0) or 0), 2),
            round(float(seg.get("end", 0) or 0), 2),
            (seg.get("text") or "").strip(),
        )
        if key not in seen:
            seen.add(key)
            deduped.append(seg)

    deduped.sort(key=lambda s: float(s.get("start", 0) or 0))

    full_text = "\n".join(
        f"{s['speaker']}: {s['text']}"
        for s in deduped if s.get("text")
    )

    result = {
        "meeting_id": meeting_id,
        "created_at": datetime.now().isoformat(timespec="seconds"),
        "language": language,
        "duration": round(max_duration, 2),
        "participants": sorted(participants),
        "segment_count": len(deduped),
        "segments": deduped,
        "full_text": full_text,
        "diarization_status": "completed",
    }

    # Save merged transcript back so PDF/summary can find it
    output_path = TRANSCRIPTS_DIR / f"{meeting_id}_merged.json"
    with open(output_path, "w", encoding="utf-8") as f:
        json.dump(result, f, indent=2, ensure_ascii=False)

    # Also update individual transcript files with speaker labels
    for tf in transcript_files:
        try:
            with open(tf, "r", encoding="utf-8") as f:
                data = json.load(f)
            participant = data.get("participant_name", "Speaker")
            for seg in data.get("segments", []):
                if not seg.get("speaker"):
                    seg["speaker"] = participant
            with open(tf, "w", encoding="utf-8") as f:
                json.dump(data, f, indent=2, ensure_ascii=False)
        except Exception:
            continue

    return result
