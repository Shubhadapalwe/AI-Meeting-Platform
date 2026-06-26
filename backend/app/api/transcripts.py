from fastapi import APIRouter, HTTPException
from pathlib import Path
import json

from app.services.transcription_service import transcribe_audio_file
from app.services.diarization_service import diarize

router = APIRouter()

BACKEND_ROOT = Path(__file__).resolve().parent.parent.parent
STORAGE_DIR = BACKEND_ROOT / "storage"
METADATA_DIR = STORAGE_DIR / "metadata"
TRANSCRIPTS_DIR = STORAGE_DIR / "transcripts"

TRANSCRIPTS_DIR.mkdir(parents=True, exist_ok=True)


@router.post("/transcribe/{meeting_id}")
def transcribe_all_recordings(meeting_id: str):
    """Transcribe EVERY recording for this meeting.
    Each file belongs to exactly one participant — speaker is assigned
    directly from upload metadata (100% accurate, no LiveKit events needed).
    """
    try:
        # Collect all recordings for this meeting
        all_metadata = []
        for metadata_file in METADATA_DIR.glob("*.json"):
            try:
                with open(metadata_file, "r", encoding="utf-8") as f:
                    data = json.load(f)
            except Exception:
                continue
            if data.get("meeting_id") == meeting_id and data.get("audio_path"):
                all_metadata.append(data)

        if not all_metadata:
            raise HTTPException(
                status_code=404,
                detail="No audio-ready recordings found for this meeting. "
                       "Both participants must click Start Recording first."
            )

        # Sort by created_at so we process in join order
        all_metadata.sort(key=lambda x: x.get("created_at", ""))

        # Collect ALL participant names expected in this meeting
        all_participants = list(dict.fromkeys(
            m.get("participant_name", "Unknown")
            for m in all_metadata
            if m.get("participant_name")
        ))

        # ── Diarization strategy ──────────────────────────────────────────────
        # ONE recording  → AssemblyAI diarizes it into multiple speakers
        #                  (both voices in one file, AI separates them)
        # MULTIPLE files → each file = one known speaker, no AI diarization
        #                  needed (per-device recording is already separated)
        use_diarization = len(all_metadata) == 1

        results = []
        for recording in all_metadata:
            participant_name = recording.get("participant_name", "Unknown")
            audio_path = recording["audio_path"]

            result = transcribe_audio_file(
                audio_path=audio_path,
                meeting_id=meeting_id,
                participant_name=participant_name,
                all_participants=all_participants,
                use_diarization=use_diarization,
            )
            results.append(result)

        return {
            "message": f"Transcribed {len(results)} recording(s) successfully",
            "recordings_processed": len(results),
            "transcripts": [r["transcript"] for r in results],
        }

    except HTTPException:
        raise
    except Exception as error:
        raise HTTPException(status_code=500, detail=str(error))


@router.post("/diarize/{meeting_id}")
def diarize_transcript(meeting_id: str):
    try:
        result = diarize(meeting_id)
        return {
            "message": "Speaker identification completed",
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
        try:
            with open(transcript_file, "r", encoding="utf-8") as f:
                data = json.load(f)
            if data.get("meeting_id") == meeting_id:
                transcripts.append(data)
        except Exception:
            continue
    return {"meeting_id": meeting_id, "transcripts": transcripts}
