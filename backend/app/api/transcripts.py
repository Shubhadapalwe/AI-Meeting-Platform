from fastapi import APIRouter, HTTPException
from pathlib import Path
import json

from app.services.transcription_service import transcribe_audio_file
from app.services.diarization_service import diarize

router = APIRouter()

BACKEND_ROOT = Path(__file__).resolve().parent.parent.parent
STORAGE_DIR = BACKEND_ROOT / "storage"
AUDIO_DIR = STORAGE_DIR / "audio"
METADATA_DIR = STORAGE_DIR / "metadata"
TRANSCRIPTS_DIR = STORAGE_DIR / "transcripts"

TRANSCRIPTS_DIR.mkdir(parents=True, exist_ok=True)


@router.post("/transcribe/{meeting_id}")
def transcribe_latest_recording(meeting_id: str):
    try:
        matching_metadata = []

        for metadata_file in METADATA_DIR.glob("*.json"):
            with open(metadata_file, "r", encoding="utf-8") as f:
                data = json.load(f)

            if data.get("meeting_id") == meeting_id and data.get("audio_path"):
                matching_metadata.append(data)

        if not matching_metadata:
            raise HTTPException(
                status_code=404,
                detail="No audio-ready recording found for this meeting"
            )

        latest_recording = sorted(
            matching_metadata,
            key=lambda x: x.get("created_at", ""),
            reverse=True
        )[0]

        return transcribe_audio_file(
            audio_path=latest_recording["audio_path"],
            meeting_id=meeting_id
        )

    except HTTPException:
        raise
    except Exception as error:
        raise HTTPException(status_code=500, detail=str(error))


@router.post("/diarize/{meeting_id}")
def diarize_transcript(meeting_id: str):
    try:
        result = diarize(meeting_id)
        return {
            "message": "Diarization completed",
            "transcript": result,
        }
    except FileNotFoundError as e:
        raise HTTPException(status_code=404, detail=str(e))
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/{meeting_id}")
def get_transcripts(meeting_id: str):
    transcripts = []

    for transcript_file in TRANSCRIPTS_DIR.glob("*.json"):
        with open(transcript_file, "r", encoding="utf-8") as f:
            data = json.load(f)

        if data.get("meeting_id") == meeting_id:
            transcripts.append(data)

    return {
        "meeting_id": meeting_id,
        "transcripts": transcripts
    }