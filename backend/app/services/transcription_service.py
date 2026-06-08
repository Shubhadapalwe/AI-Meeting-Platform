from pathlib import Path
from datetime import datetime
from faster_whisper import WhisperModel
import json
import uuid

# Anchor to backend root so paths are correct regardless of launch directory
BACKEND_ROOT = Path(__file__).resolve().parent.parent.parent
STORAGE_DIR = BACKEND_ROOT / "storage"
AUDIO_DIR = STORAGE_DIR / "audio"
TRANSCRIPTS_DIR = STORAGE_DIR / "transcripts"

TRANSCRIPTS_DIR.mkdir(parents=True, exist_ok=True)

_model = None


def get_whisper_model():
    global _model

    if _model is None:
        _model = WhisperModel(
            "base",
            device="cpu",
            compute_type="int8"
        )

    return _model


def transcribe_audio_file(audio_path: str, meeting_id: str):
    audio_file = Path(audio_path)

    if not audio_file.exists():
        raise FileNotFoundError(f"Audio file not found: {audio_path}")

    model = get_whisper_model()

    segments_generator, info = model.transcribe(
        str(audio_file),
        beam_size=5,
        vad_filter=True
    )

    # Force-consume the lazy generator immediately so we capture all segments
    transcript_segments = []
    for segment in segments_generator:
        transcript_segments.append({
            "start": round(segment.start, 2),
            "end": round(segment.end, 2),
            "text": segment.text.strip(),
            "speaker": None  # populated later by diarization
        })

    transcript_id = str(uuid.uuid4())
    transcript_filename = f"{meeting_id}_{transcript_id}.json"
    transcript_path = TRANSCRIPTS_DIR / transcript_filename

    transcript_data = {
        "transcript_id": transcript_id,
        "meeting_id": meeting_id,
        "audio_path": str(audio_file),
        "language": info.language,
        "language_probability": round(info.language_probability, 3),
        "duration": round(info.duration, 2),
        "created_at": datetime.now().isoformat(timespec="seconds"),
        "segments": transcript_segments,
        "full_text": " ".join([s["text"] for s in transcript_segments])
    }

    with open(transcript_path, "w", encoding="utf-8") as f:
        json.dump(transcript_data, f, indent=2, ensure_ascii=False)

    return {
        "message": "Transcription completed successfully",
        "transcript_path": str(transcript_path),
        "transcript": transcript_data
    }