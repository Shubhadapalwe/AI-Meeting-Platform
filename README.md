# AI Meeting Intelligence Platform

A Zoom-like meeting system with a Fathom-style AI assistant.

## Current Version

Phase 2: Realtime Meeting Infrastructure

This version converts the Phase 1 static meeting UI into a real WebRTC meeting foundation using LiveKit.

## Phase 2 Included

- FastAPI backend foundation
- React + Vite frontend
- LiveKit local media server through Docker Compose
- Backend LiveKit token generation endpoint
- Realtime room join flow
- Camera and microphone publishing
- Remote participant video tiles
- Mute/unmute control
- Camera on/off control
- Screen sharing control
- Active speaker visual highlight
- Participant event logging API
- Mock AI notes panel kept for future AI pipeline
- PostgreSQL and Redis services prepared for next phases

## Why Phase 2 is important

The AI modules depend on meeting data. Before transcription, diarization, summaries, and Ask-AI, the product needs reliable realtime meeting infrastructure.

This phase captures the metadata required later for speaker mapping:

- participant joined
- participant left
- mic changed
- camera changed
- screen share changed
- active speaker detected

This data will help improve diarization beyond pure audio-only detection.

## Project Structure

```text
meeting-ai-platform/
├── backend/
│   ├── app/
│   │   ├── api/
│   │   ├── core/
│   │   ├── schemas/
│   │   └── services/
│   ├── requirements.txt
│   └── Dockerfile
├── frontend/
│   ├── src/
│   │   ├── services/
│   │   ├── main.jsx
│   │   └── styles.css
│   ├── package.json
│   └── Dockerfile
├── ai/
├── docker-compose.yml
└── README.md
```

## Run Recommended Way: Docker Compose

From project root:

```bash
docker compose up --build
```

Open frontend:

```text
http://localhost:5173
```

Backend health check:

```text
http://localhost:8000/health
```

LiveKit server:

```text
ws://localhost:7880
```

## Run Without Docker

Use this only if LiveKit server is already running separately.

### Backend

```bash
cd backend
python3 -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
cp .env.example .env
uvicorn app.main:app --reload --port 8000
```

### Frontend

Open a new terminal:

```bash
cd frontend
npm install
npm run dev
```

Open:

```text
http://localhost:5173
```

## How to Test Phase 2

1. Run Docker Compose.
2. Open `http://localhost:5173`.
3. Create a meeting.
4. Click Join Meeting.
5. Allow camera and microphone permissions.
6. Copy the meeting link.
7. Open the same link in another browser tab or another browser.
8. Join as a different name.
9. Test:
   - mute/unmute
   - camera on/off
   - screen share
   - active speaker highlight
   - participant list

## Current API Endpoints

```text
GET  /health
POST /api/meetings/create
GET  /api/meetings/{meeting_id}
POST /api/livekit/token
POST /api/participants/events
GET  /api/participants/events/{meeting_id}
POST /api/ai/mock-summary
```

## Next Phase

Phase 3: Recording and Audio Capture Pipeline

Planned work:

- start/stop recording button
- meeting recording status
- audio extraction using FFmpeg
- storage folder structure
- recording metadata table design
- prepare audio for Whisper transcription

## Phase 2.1 Multi-Participant Local Test Fix

This version improves the 3-4 participant test:

- LiveKit advertises `127.0.0.1` as the node IP for local Docker testing.
- Direct meeting links now ask each participant to enter a unique name.
- Video grid is stabilized for 1-4 participants.
- Participant panel shows live count.

Use different browsers for local testing: Chrome normal, Chrome Incognito, Safari, Firefox.
