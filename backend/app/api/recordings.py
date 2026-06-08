from fastapi import APIRouter, UploadFile, File, Form, HTTPException
from pathlib import Path
from datetime import datetime
import shutil
import subprocess
import json
import uuid

router = APIRouter()

# Anchor storage to the backend root so it works regardless of launch directory
BACKEND_ROOT = Path(__file__).resolve().parent.parent.parent
STORAGE_DIR = BACKEND_ROOT / "storage"
RECORDINGS_DIR = STORAGE_DIR / "recordings"
AUDIO_DIR = STORAGE_DIR / "audio"
METADATA_DIR = STORAGE_DIR / "metadata"

RECORDINGS_DIR.mkdir(parents=True, exist_ok=True)
AUDIO_DIR.mkdir(parents=True, exist_ok=True)
METADATA_DIR.mkdir(parents=True, exist_ok=True)


@router.post("/upload")
async def upload_recording(
    meeting_id: str = Form(...),
    participant_name: str = Form("unknown"),
    file: UploadFile = File(...),
):
    recording_id = str(uuid.uuid4())
    created_at = datetime.now().isoformat(timespec="seconds")

    safe_meeting_id = meeting_id.replace("/", "_").replace(" ", "_")
    video_filename = f"{safe_meeting_id}_{recording_id}.webm"
    audio_filename = f"{safe_meeting_id}_{recording_id}.wav"
    metadata_filename = f"{safe_meeting_id}_{recording_id}.json"

    video_path = RECORDINGS_DIR / video_filename
    audio_path = AUDIO_DIR / audio_filename
    metadata_path = METADATA_DIR / metadata_filename

    try:
        with open(video_path, "wb") as buffer:
            shutil.copyfileobj(file.file, buffer)

        ffmpeg_command = [
            "ffmpeg",
            "-y",
            "-i",
            str(video_path),
            "-vn",
            "-acodec",
            "pcm_s16le",
            "-ar",
            "16000",
            "-ac",
            "1",
            str(audio_path),
        ]

        result = subprocess.run(
            ffmpeg_command,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            text=True,
        )

        audio_extraction_status = "audio_ready_for_whisper"
        final_audio_path = str(audio_path)
        ffmpeg_error = None

        if result.returncode != 0:
            audio_extraction_status = "video_saved_audio_extraction_failed"
            final_audio_path = None
            ffmpeg_error = result.stderr

        metadata = {
            "recording_id": recording_id,
            "meeting_id": meeting_id,
            "participant_name": participant_name,
            "original_filename": file.filename,
            "video_path": str(video_path),
            "audio_path": final_audio_path,
            "metadata_path": str(metadata_path),
            "created_at": created_at,
            "status": audio_extraction_status,
            "ffmpeg_error": ffmpeg_error,
        }

        with open(metadata_path, "w", encoding="utf-8") as f:
            json.dump(metadata, f, indent=2)

        return {
            "message": "Recording uploaded successfully",
            "recording": metadata,
        }

    except Exception as error:
        raise HTTPException(status_code=500, detail=str(error))


@router.get("/{meeting_id}")
def list_recordings_for_meeting(meeting_id: str):
    recordings = []

    for metadata_file in METADATA_DIR.glob("*.json"):
        with open(metadata_file, "r", encoding="utf-8") as f:
            data = json.load(f)
            if data.get("meeting_id") == meeting_id:
                recordings.append(data)

    return {"meeting_id": meeting_id, "recordings": recordings}