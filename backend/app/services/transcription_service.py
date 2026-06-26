"""
Transcription + Speaker Diarization service

Priority order:
  1. Sarvam AI  — if SARVAM_API_KEY is set
                   Saaras v3 model, supports 22 Indian languages + English,
                   code-mixing (Hinglish), built-in speaker diarization via
                   Batch API. Best for India-specific meetings.
  2. AssemblyAI — if ASSEMBLYAI_API_KEY is set
                   Good English accuracy, built-in diarization.
  3. WhisperX   — local, no API key needed, speaker label from metadata.
  4. faster-whisper — local fallback.

Strategy:
  ONE recording file  → AI diarization (auto-detect multiple speakers)
  MULTIPLE files      → each file = one participant, label all segments with
                         that person's name (100% accurate, no AI confusion)
"""

import os
import json
import tempfile
import time
import uuid
import requests
from pathlib import Path
from datetime import datetime

BACKEND_ROOT = Path(__file__).resolve().parent.parent.parent
STORAGE_DIR  = BACKEND_ROOT / "storage"
TRANSCRIPTS_DIR = STORAGE_DIR / "transcripts"
TRANSCRIPTS_DIR.mkdir(parents=True, exist_ok=True)

SARVAM_API_KEY     = os.getenv("SARVAM_API_KEY", "")
ASSEMBLYAI_API_KEY = os.getenv("ASSEMBLYAI_API_KEY", "")

_whisper_model  = None
_whisperx_model = None


# ── Sarvam AI (best for Indian languages) ─────────────────────────────────────

def _sarvam_transcribe(audio_path: str, all_participants: list, use_diarization: bool):
    """
    Use Sarvam Batch API (Saaras v3) for transcription + optional diarization.
    Returns (segments, language).
    """
    headers = {"api-subscription-key": SARVAM_API_KEY, "Content-Type": "application/json"}
    base    = "https://api.sarvam.ai/speech-to-text/job/v1"

    job_params = {
        "model": "saaras:v3",
        "language_code": "unknown",   # auto-detect language
        "mode": "transcribe",
        "with_diarization": use_diarization,
    }
    if use_diarization and all_participants:
        # Hint the number of speakers; Sarvam auto-detects if omitted
        n = min(len(all_participants), 10)
        if n >= 2:
            job_params["num_speakers"] = n

    # 1. Create job
    r = requests.post(base, headers=headers, json={"job_parameters": job_params})
    r.raise_for_status()
    job_id = r.json()["job_id"]

    # 2. Get upload URL
    filename = Path(audio_path).name
    r = requests.post(
        f"{base}/upload-files", headers=headers,
        json={"job_id": job_id, "files": [filename]},
    )
    r.raise_for_status()
    upload_url = r.json()["upload_urls"][filename]["file_url"]

    # 3. Upload file
    with open(audio_path, "rb") as f:
        up = requests.put(
            upload_url, data=f,
            headers={"x-ms-blob-type": "BlockBlob", "Content-Type": "audio/webm"},
        )
        up.raise_for_status()

    # 4. Start job
    r = requests.post(f"{base}/{job_id}/start", headers={"api-subscription-key": SARVAM_API_KEY})
    r.raise_for_status()

    # 5. Poll until complete (max 10 min)
    for _ in range(120):
        time.sleep(5)
        r = requests.get(f"{base}/{job_id}/status", headers={"api-subscription-key": SARVAM_API_KEY})
        r.raise_for_status()
        status = r.json()
        state  = status.get("job_state", "")
        if state == "Completed":
            break
        if state in ("Failed", "Cancelled"):
            raise RuntimeError(f"Sarvam job {state}: {status}")
    else:
        raise RuntimeError("Sarvam job timed out after 10 minutes")

    # 6. Get download URL for result
    details   = status.get("job_details", [])
    out_files = [o["file_name"] for d in details for o in d.get("outputs", [])]
    if not out_files:
        raise RuntimeError("Sarvam returned no output files")

    r = requests.post(
        f"{base}/download-files", headers=headers,
        json={"job_id": job_id, "files": out_files},
    )
    r.raise_for_status()
    dl_urls = r.json()["download_urls"]

    # 7. Download and parse first result file
    first_url  = dl_urls[out_files[0]]["file_url"]
    result     = requests.get(first_url).json()
    lang       = result.get("language_code", "en-IN")

    if use_diarization and "diarized_transcript" in result:
        entries = result["diarized_transcript"].get("entries", [])
        # Map speaker_id → participant name in order of first appearance
        speaker_map: dict[str, str] = {}
        def resolve(sid: str) -> str:
            if sid not in speaker_map:
                idx = len(speaker_map)
                speaker_map[sid] = (
                    all_participants[idx] if idx < len(all_participants)
                    else f"Speaker {int(sid)+1}"
                )
            return speaker_map[sid]

        segments = [
            {
                "start":   round(float(e.get("start_time_seconds", 0)), 2),
                "end":     round(float(e.get("end_time_seconds",   0)), 2),
                "text":    e.get("transcript", "").strip(),
                "speaker": resolve(str(e.get("speaker_id", "0"))),
            }
            for e in entries
        ]
    else:
        # No diarization — use full transcript text as single block
        full_text = result.get("transcript", "")
        words     = result.get("timestamps", {})
        starts    = words.get("start_time_seconds", [])
        ends      = words.get("end_time_seconds",   [])
        texts     = words.get("words", [])

        if texts and starts:
            # Group words into ~sentence chunks
            segments = []
            chunk_words, chunk_start, chunk_end = [], 0.0, 0.0
            for i, (w, s, e) in enumerate(zip(texts, starts, ends)):
                if not chunk_words:
                    chunk_start = s
                chunk_words.append(w)
                chunk_end = e
                if w.endswith((".", "?", "!")) or i == len(texts) - 1:
                    segments.append({
                        "start": round(chunk_start, 2),
                        "end":   round(chunk_end, 2),
                        "text":  " ".join(chunk_words),
                    })
                    chunk_words = []
        else:
            segments = [{"start": 0.0, "end": 0.0, "text": full_text}] if full_text else []

    return segments, lang.split("-")[0]  # "en-IN" → "en"


# ── AssemblyAI ─────────────────────────────────────────────────────────────────

def _assemblyai_transcribe(audio_path: str, all_participants: list):
    import assemblyai as aai
    aai.settings.api_key = ASSEMBLYAI_API_KEY
    n = len(all_participants)
    config = aai.TranscriptionConfig(
        speaker_labels=True,
        speakers_expected=n if n >= 2 else None,
        language_detection=True,
    )
    transcript = aai.Transcriber().transcribe(audio_path, config=config)
    if transcript.status == aai.TranscriptStatus.error:
        raise RuntimeError(f"AssemblyAI error: {transcript.error}")

    speaker_map: dict[str, str] = {}
    def resolve(label: str) -> str:
        if label not in speaker_map:
            idx = len(speaker_map)
            speaker_map[label] = (
                all_participants[idx] if idx < len(all_participants)
                else f"Speaker {label}"
            )
        return speaker_map[label]

    segments = [
        {
            "start":   round(u.start / 1000, 2),
            "end":     round(u.end   / 1000, 2),
            "text":    u.text.strip(),
            "speaker": resolve(u.speaker),
        }
        for u in (transcript.utterances or [])
    ]
    return segments, (transcript.language_code or "en")


def _assemblyai_single(audio_path: str, participant_name: str):
    import assemblyai as aai
    aai.settings.api_key = ASSEMBLYAI_API_KEY
    config = aai.TranscriptionConfig(speaker_labels=False, language_detection=True)
    transcript = aai.Transcriber().transcribe(audio_path, config=config)
    if transcript.status == aai.TranscriptStatus.error:
        raise RuntimeError(f"AssemblyAI error: {transcript.error}")
    segments = [
        {
            "start":   round(s.start / 1000, 2),
            "end":     round(s.end   / 1000, 2),
            "text":    s.text.strip(),
            "speaker": participant_name,
        }
        for s in (transcript.get_sentences() or [])
    ] or [{"start": 0.0, "end": 0.0, "text": transcript.text or "", "speaker": participant_name}]
    return segments, (transcript.language_code or "en")


# ── Local fallback ─────────────────────────────────────────────────────────────

def _get_faster_whisper():
    global _whisper_model
    if _whisper_model is None:
        from faster_whisper import WhisperModel
        _whisper_model = WhisperModel("small", device="cpu", compute_type="int8")
    return _whisper_model


def _try_whisperx(audio_path: str):
    import whisperx, torch
    global _whisperx_model
    device = "cuda" if torch.cuda.is_available() else "cpu"
    compute_type = "float16" if device == "cuda" else "int8"
    if _whisperx_model is None:
        _whisperx_model = whisperx.load_model("small", device, compute_type=compute_type)
    audio  = whisperx.load_audio(audio_path)
    result = _whisperx_model.transcribe(audio, batch_size=8)
    try:
        model_a, metadata = whisperx.load_align_model(
            language_code=result["language"], device=device
        )
        result = whisperx.align(result["segments"], model_a, metadata, audio, device,
                                return_char_alignments=False)
    except Exception:
        pass
    segments = [
        {"start": round(float(s.get("start", 0)), 2),
         "end":   round(float(s.get("end",   0)), 2),
         "text":  s.get("text", "").strip()}
        for s in result.get("segments", [])
    ]
    return segments, result.get("language", "unknown")


def _faster_whisper_transcribe(audio_path: str):
    model = _get_faster_whisper()
    segs, info = model.transcribe(audio_path, beam_size=5, vad_filter=True)
    return [{"start": round(s.start, 2), "end": round(s.end, 2), "text": s.text.strip()}
            for s in segs], info.language


def _local_transcribe(audio_path: str, participant_name: str):
    try:
        segments, language = _try_whisperx(audio_path)
        engine = "whisperx"
    except Exception:
        segments, language = _faster_whisper_transcribe(audio_path)
        engine = "faster_whisper"
    for seg in segments:
        seg["speaker"] = participant_name
    return segments, language, engine


# ── Public entry point ─────────────────────────────────────────────────────────

def transcribe_audio_file(
    audio_path: str,
    meeting_id: str,
    participant_name: str = "Unknown",
    all_participants: list = None,
    use_diarization: bool = False,
    known_participants: list = None,   # legacy compat
):
    audio_file = Path(audio_path)
    if not audio_file.exists():
        raise FileNotFoundError(f"Audio file not found: {audio_path}")

    # Build ordered participant list: primary speaker first
    participants = []
    if participant_name and participant_name != "Unknown":
        participants.append(participant_name)
    for p in (all_participants or known_participants or []):
        if p not in participants:
            participants.append(p)

    engine_used = "unknown"
    segments    = []
    language    = "unknown"

    # ── Sarvam AI (priority 1) ─────────────────────────────────────────────
    if SARVAM_API_KEY:
        try:
            segments, language = _sarvam_transcribe(
                str(audio_file), participants, use_diarization
            )
            engine_used = "sarvam_diarized" if use_diarization else "sarvam"
            # For single-speaker files, label all segments with participant_name
            if not use_diarization:
                for seg in segments:
                    seg["speaker"] = participant_name
        except Exception as e:
            print(f"[transcription] Sarvam failed ({e}), trying next")
            segments = []

    # ── AssemblyAI (priority 2) ────────────────────────────────────────────
    if not segments and ASSEMBLYAI_API_KEY:
        try:
            if use_diarization:
                segments, language = _assemblyai_transcribe(str(audio_file), participants)
                engine_used = "assemblyai_diarized"
            else:
                segments, language = _assemblyai_single(str(audio_file), participant_name)
                engine_used = "assemblyai"
        except Exception as e:
            print(f"[transcription] AssemblyAI failed ({e}), using local")
            segments = []

    # ── Local fallback (priority 3) ────────────────────────────────────────
    if not segments:
        segments, language, engine_used = _local_transcribe(str(audio_file), participant_name)

    speakers_found = list(dict.fromkeys(
        seg.get("speaker", participant_name) for seg in segments
    ))

    transcript_id   = str(uuid.uuid4())
    transcript_data = {
        "transcript_id":    transcript_id,
        "meeting_id":       meeting_id,
        "audio_path":       str(audio_file),
        "participant_name": participant_name,
        "language":         language,
        "duration":         round(segments[-1]["end"], 2) if segments else 0,
        "created_at":       datetime.now().isoformat(timespec="seconds"),
        "engine":           engine_used,
        "segments":         segments,
        "participants":     speakers_found,
        "full_text": "\n".join(
            f"{seg.get('speaker', participant_name)}: {seg['text']}"
            for seg in segments if seg.get("text")
        ),
    }

    path = TRANSCRIPTS_DIR / f"{meeting_id}_{transcript_id}.json"
    with open(path, "w", encoding="utf-8") as f:
        json.dump(transcript_data, f, indent=2, ensure_ascii=False)

    return {
        "message":         f"Transcription completed ({engine_used})",
        "transcript_path": str(path),
        "transcript":      transcript_data,
    }
