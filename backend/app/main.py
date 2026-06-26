import os
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import FileResponse
from pathlib import Path

from app.api.meetings import router as meeting_router
from app.api.ai import router as ai_router
from app.api.livekit import router as livekit_router
from app.api.participants import router as participant_router
from app.api.recordings import router as recording_router
from app.api.transcripts import router as transcript_router
from app.api.pdf import router as pdf_router
from app.api.meetings_merge import router as meetings_merge_router
from app.api.speakers import router as speakers_router
from app.api.email_digest import router as email_router

app = FastAPI(
    title="AI Meeting Intelligence Platform",
    description="Backend API for Zoom-like meeting system with Fathom-style AI assistant features.",
    version="0.10.0",
)

app.add_middleware(
    CORSMiddleware,
    allow_origin_regex=r"https?://(localhost|127\.0\.0\.1|192\.168\.\d+\.\d+|10\.\d+\.\d+\.\d+)(:\d+)?",
    allow_credentials=True,
    allow_methods=["GET", "POST", "PUT", "DELETE", "OPTIONS", "PATCH"],
    allow_headers=["Content-Type", "Authorization", "Accept", "Origin", "X-Requested-With"],
)

# Core APIs
app.include_router(
    meeting_router,
    prefix="/api/meetings",
    tags=["Meetings"],
)

app.include_router(
    ai_router,
    prefix="/api/ai",
    tags=["AI"],
)

app.include_router(
    livekit_router,
    prefix="/api/livekit",
    tags=["LiveKit"],
)

app.include_router(
    participant_router,
    prefix="/api/participants",
    tags=["Participants"],
)

app.include_router(
    recording_router,
    prefix="/api/recordings",
    tags=["Recordings"],
)

app.include_router(
    transcript_router,
    prefix="/api/transcripts",
    tags=["Transcripts"],
)

app.include_router(
    pdf_router,
    prefix="/api/pdf",
    tags=["PDF"],
)

# Phase 9.1 - Meeting Transcript Aggregation
app.include_router(
    meetings_merge_router,
    prefix="/api/meetings",
    tags=["Meeting Aggregation"],
)

# Phase 9.2 - Speaker Analytics
app.include_router(
    speakers_router,
    prefix="/api/speakers",
    tags=["Speaker Analytics"],
)

# Phase 10 - Email Digest
app.include_router(
    email_router,
    prefix="/api/email",
    tags=["Email Digest"],
)

@app.get("/")

def root():
    return {
        "name": "AI Meeting Intelligence Platform",
        "version": "0.9.1",
        "status": "running",
    }


@app.get("/rootca")
def download_rootca():
    """Serve the mkcert root CA so Android devices can import and trust it."""
    ca_path = Path("/certs/rootCA.pem")
    if not ca_path.exists():
        return {"error": "Root CA not found. Run bash start.sh first."}
    return FileResponse(
        ca_path,
        media_type="application/x-pem-file",
        filename="rootCA.pem",
    )


@app.get("/health")

def health_check():
    return {
        "status": "ok",
        "version": "0.9.1",
        "message": (
            "Backend running with "
            "Transcription, Diarization, AI Summary, "
            "Ask AI, PDF Generation and Meeting Aggregation"
        ),
    }