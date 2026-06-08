from pathlib import Path
from datetime import datetime
import json

BACKEND_ROOT = Path(__file__).resolve().parent.parent.parent
STORAGE_DIR = BACKEND_ROOT / "storage"

TRANSCRIPTS_DIR = STORAGE_DIR / "transcripts"
EVENTS_DIR = STORAGE_DIR / "events"
METADATA_DIR = STORAGE_DIR / "metadata"
MEETINGS_DIR = STORAGE_DIR / "meetings"

MEETINGS_DIR.mkdir(parents=True, exist_ok=True)


def load_json_file(path: Path):
    if not path.exists():
        return None

    with open(path, "r", encoding="utf-8") as f:
        return json.load(f)


def load_events(meeting_id: str):
    event_file = EVENTS_DIR / f"{meeting_id}.json"
    data = load_json_file(event_file)

    if isinstance(data, list):
        return data

    return []


def parse_time(value):
    if not value:
        return None

    try:
        return datetime.fromisoformat(str(value).replace("Z", "+00:00"))
    except Exception:
        return None


def clean_speaker_name(value):
    if not value:
        return None

    value = str(value).strip()

    bad_names = {
        "speaker",
        "speaker 1",
        "unknown",
        "none",
        "null",
        "",
    }

    if value.lower() in bad_names:
        return None

    return value


def load_recording_metadata_participant(transcript: dict):
    audio_path = transcript.get("audio_path")

    if not audio_path:
        return None

    audio_stem = Path(audio_path).stem
    metadata_file = METADATA_DIR / f"{audio_stem}.json"

    metadata = load_json_file(metadata_file)

    if not metadata:
        return None

    return clean_speaker_name(
        metadata.get("participant_name")
        or metadata.get("speaker")
        or metadata.get("name")
    )


def build_speaker_timeline(events):
    speaker_events = [
        event
        for event in events
        if event.get("event_type") == "active_speaker"
        and clean_speaker_name(event.get("participant_name"))
    ]

    if not speaker_events:
        return []

    # Prefer "recording_started" as the anchor — its wall-clock time matches
    # offset 0:00 in the whisper transcript.  Fall back to the earliest join
    # event, then to the earliest event of any type.
    recording_start_events = [
        parse_time(event.get("created_at"))
        for event in events
        if event.get("event_type") == "recording_started"
        and parse_time(event.get("created_at"))
    ]
    if recording_start_events:
        start_time = min(recording_start_events)
    else:
        join_times = [
            parse_time(event.get("created_at"))
            for event in events
            if event.get("event_type") == "joined"
            and parse_time(event.get("created_at"))
        ]
        if join_times:
            start_time = min(join_times)
        else:
            all_times = [
                parse_time(event.get("created_at"))
                for event in events
                if parse_time(event.get("created_at"))
            ]
            if not all_times:
                return []
            start_time = min(all_times)

    timeline = []

    for event in speaker_events:
        event_time = parse_time(event.get("created_at"))

        if not event_time:
            continue

        offset = (event_time - start_time).total_seconds()

        timeline.append(
            {
                "offset": max(offset, 0),
                "participant_name": clean_speaker_name(
                    event.get("participant_name")
                ),
            }
        )

    timeline.sort(key=lambda item: item["offset"])
    return timeline


def find_speaker_for_segment(timeline, segment):
    if not timeline:
        return None

    start = float(segment.get("start", 0) or 0)
    end = float(segment.get("end", start) or start)
    midpoint = (start + end) / 2

    selected = timeline[0]["participant_name"]

    for item in timeline:
        if item["offset"] <= midpoint:
            selected = item["participant_name"]
        else:
            break

    return selected


def aggregate_meeting_transcripts(meeting_id: str):
    transcript_files = list(TRANSCRIPTS_DIR.glob(f"{meeting_id}_*.json"))

    if not transcript_files:
        raise FileNotFoundError(f"No transcripts found for meeting {meeting_id}")

    transcript_files.sort(key=lambda file: file.stat().st_mtime)

    events = load_events(meeting_id)
    speaker_timeline = build_speaker_timeline(events)

    joined_participants = {
        clean_speaker_name(event.get("participant_name"))
        for event in events
        if clean_speaker_name(event.get("participant_name"))
    }

    merged_segments = []
    participants = set()
    full_text_parts = []
    duration = 0
    language = "unknown"

    for transcript_file in transcript_files:
        transcript = load_json_file(transcript_file)

        if not transcript:
            continue

        duration = max(duration, float(transcript.get("duration", 0) or 0))
        language = transcript.get("language", language)

        metadata_speaker = load_recording_metadata_participant(transcript)

        for segment in transcript.get("segments", []):
            segment = dict(segment)

            speaker = clean_speaker_name(segment.get("speaker"))

            if not speaker:
                speaker = find_speaker_for_segment(speaker_timeline, segment)

            if not speaker:
                speaker = metadata_speaker

            if not speaker and len(joined_participants) == 1:
                speaker = list(joined_participants)[0]

            if not speaker:
                speaker = "Speaker"

            segment["speaker"] = speaker

            participants.add(speaker)
            merged_segments.append(segment)

    # Deduplicate: multiple transcript files for the same meeting (e.g. transcription
    # triggered twice) produce identical segments. Remove by (start, end, text) key.
    seen_keys: set = set()
    deduped: list = []
    for seg in merged_segments:
        key = (
            round(float(seg.get("start", 0) or 0), 2),
            round(float(seg.get("end", 0) or 0), 2),
            (seg.get("text") or "").strip(),
        )
        if key not in seen_keys:
            seen_keys.add(key)
            deduped.append(seg)
    merged_segments = deduped

    merged_segments.sort(key=lambda item: float(item.get("start", 0) or 0))

    for segment in merged_segments:
        speaker = segment.get("speaker", "Speaker")
        text = segment.get("text", "")

        if text:
            full_text_parts.append(f"{speaker}: {text}")

    merged = {
        "meeting_id": meeting_id,
        "created_at": datetime.now().isoformat(timespec="seconds"),
        "language": language,
        "duration": round(duration, 2),
        "participants": sorted(list(participants)),
        "segment_count": len(merged_segments),
        "segments": merged_segments,
        "full_text": "\n".join(full_text_parts),
    }

    output_file = MEETINGS_DIR / f"{meeting_id}_merged.json"

    with open(output_file, "w", encoding="utf-8") as f:
        json.dump(merged, f, indent=2, ensure_ascii=False)

    return merged