# 🎙️ AI Meeting Intelligence Platform

A self-hosted, Fathom-style AI meeting assistant with real-time WebRTC video, automatic transcription in Indian languages, speaker diarization, AI-generated summaries, and email delivery — all running on your own machine.

---

## ✨ Features

- **Video Meetings** — Real-time WebRTC rooms via LiveKit (camera, mic, screen share, mute)
- **Recording** — Host records directly from the browser (no plugins)
- **Transcription** — Sarvam AI (22 Indian languages + Hinglish) → AssemblyAI → WhisperX (fully offline fallback)
- **Speaker Diarization** — Automatically identifies who said what, mapped to participant names
- **AI Summary** — Short summary, key takeaways, action items, decisions, next steps
- **Ask AI** — Chat with your meeting transcript ("What did Shubhada say about the deadline?")
- **PDF Export** — Professional meeting report, auto-generated
- **Email Delivery** — Summary + PDF sent to all participants after the meeting
- **Android Support** — Join from any device on the same WiFi network
- **Offline-capable** — Runs entirely on your machine with local Whisper models

---

## 🛠️ Tech Stack

| Layer | Technology |
|---|---|
| Frontend | React 18 + Vite, LiveKit JS SDK |
| Backend | FastAPI (Python 3.11) |
| Database | PostgreSQL + Redis |
| Video/Audio | LiveKit (self-hosted) |
| Transcription | Sarvam AI (Saaras v3) → AssemblyAI → WhisperX → faster-whisper |
| AI Summary | Sarvam-M → Gemini 1.5 Flash → extractive fallback |
| PDF | ReportLab |
| Infrastructure | Docker Compose |

---

## 🚀 Quick Start

### Prerequisites

- Docker Desktop installed and running
- Mac or Linux (Windows with WSL2 should work)

### 1. Clone the repo

```bash
git clone https://github.com/YOUR_USERNAME/meeting-ai-platform.git
cd meeting-ai-platform
```

### 2. Set up environment variables

```bash
cp .env.example .env
```

Edit `.env` with your credentials (see [Environment Variables](#-environment-variables) below).

### 3. Start everything

```bash
bash start.sh
```

This will:
- Detect your Mac's WiFi IP automatically
- Generate self-signed SSL certificates (required for microphone access in browser)
- Start all Docker services (backend, frontend, LiveKit, PostgreSQL, Redis)

### 4. Open the app

```
https://localhost:5173
```

> Accept the browser's SSL warning (self-signed cert for local use). This is normal.

### 5. Join from Android

On the same WiFi network, open:

```
https://192.168.x.x:5173
```

Replace with your Mac's actual IP (shown when `start.sh` runs).

---

## 🔑 Environment Variables

Copy `.env.example` to `.env` and fill in:

```env
# ── Network ──────────────────────────────────────────────────────────────────
# Your Mac's WiFi IP — find it with: ipconfig getifaddr en0
HOST_IP=192.168.1.xxx

# ── Sarvam AI (BEST for Indian languages) ────────────────────────────────────
# Supports Hindi, Marathi, Tamil, Telugu, Bengali + Hinglish code-mixing
# Also used for AI summary (Sarvam-M model)
# Get FREE key at: https://dashboard.sarvam.ai → API Keys
SARVAM_API_KEY=sk_...

# ── AssemblyAI (fallback diarization) ────────────────────────────────────────
# FREE 100 hours/month
# Get key at: https://www.assemblyai.com → Account → API Keys
ASSEMBLYAI_API_KEY=...

# ── Gemini (fallback AI summary) ─────────────────────────────────────────────
# FREE at: https://aistudio.google.com → Get API Key
GEMINI_API_KEY=...

# ── Email (optional) ─────────────────────────────────────────────────────────
# For Gmail: enable 2FA, then create App Password at:
# https://myaccount.google.com/apppasswords
# Without this, emails are saved locally but not sent.
SMTP_HOST=smtp.gmail.com
SMTP_PORT=587
SMTP_USER=you@gmail.com
SMTP_PASSWORD=xxxx xxxx xxxx xxxx
EMAIL_FROM=you@gmail.com
```

If no API keys are set, the system falls back to local WhisperX (offline, no cost).

---

## 🏗️ Project Structure

```
meeting-ai-platform/
├── backend/
│   ├── app/
│   │   ├── api/               # FastAPI route handlers
│   │   │   ├── meetings.py
│   │   │   ├── transcripts.py
│   │   │   ├── ai.py
│   │   │   ├── email.py
│   │   │   └── pdf.py
│   │   ├── services/          # Business logic
│   │   │   ├── transcription_service.py  # Sarvam → AssemblyAI → Whisper
│   │   │   ├── ai_service.py             # Summary + Ask AI
│   │   │   ├── pdf_service.py
│   │   │   └── email_service.py
│   │   ├── schemas/           # Pydantic models
│   │   └── main.py
│   ├── storage/               # Runtime data (gitignored)
│   │   ├── recordings/
│   │   ├── transcripts/
│   │   ├── summaries/
│   │   └── pdfs/
│   ├── requirements.txt
│   └── Dockerfile
├── frontend/
│   ├── src/
│   │   ├── components/
│   │   │   ├── RecordingControls.jsx    # Audio capture + diarization trigger
│   │   │   ├── MeetingRoom.jsx          # Main video room
│   │   │   ├── TranscriptPanel.jsx
│   │   │   ├── SummaryPanel.jsx
│   │   │   └── AskAIPanel.jsx
│   │   ├── pages/
│   │   │   ├── LandingPage.jsx
│   │   │   └── MeetingPage.jsx
│   │   └── main.jsx
│   ├── vite.config.js         # Includes LiveKit WebSocket proxy
│   ├── package.json
│   └── Dockerfile
├── certs/                     # Auto-generated SSL certs (gitignored)
├── docker-compose.yml
├── start.sh                   # One-command startup script
├── .env.example
└── .gitignore
```

---

## 🧠 How Transcription Works

```
Single recording file (host only)
    └─► AI Diarization enabled
            ├─ Sarvam Saaras v3 Batch API  (best for Indian languages)
            ├─ AssemblyAI                   (fallback)
            └─ WhisperX local              (offline fallback)

Multiple recording files (each participant records)
    └─► Each file labelled with that participant's name (100% accurate)
            ├─ Sarvam Saaras v3 (no diarization needed)
            ├─ AssemblyAI single-speaker
            └─ WhisperX / faster-whisper
```

Speaker names are mapped in order of first appearance: the host maps to `SPEAKER_0`, the next detected speaker to `SPEAKER_1`, and so on.

---

## 🤖 AI Summary Priority Chain

```
OpenAI GPT-4o-mini  (if OPENAI_API_KEY set)
    ↓ fallback
Sarvam-M            (optimized for Indian context + languages)
    ↓ fallback
Gemini 1.5 Flash    (free quota)
    ↓ fallback
Extractive summary  (offline, no API key needed)
```

---

## 📡 API Endpoints

```
GET  /health
POST /api/meetings/create
GET  /api/meetings/{meeting_id}
POST /api/livekit/token
POST /api/participants/events
POST /api/recordings/upload
POST /api/transcripts/process/{meeting_id}
GET  /api/transcripts/{meeting_id}
POST /api/ai/summary/{meeting_id}
POST /api/ai/ask/{meeting_id}
GET  /api/ai/analytics/{meeting_id}
GET  /api/pdf/{meeting_id}
POST /api/email/send/{meeting_id}
```

---

## 🔧 Manual Docker Commands

```bash
# Start all services
docker compose up -d --build

# View logs
docker compose logs -f backend
docker compose logs -f frontend

# Restart a single service
docker compose restart backend

# Stop everything
docker compose down

# Full reset (clears database)
docker compose down -v
```

---

## 🌐 Supported Languages

Powered by Sarvam AI Saaras v3:

Assamese, Bengali, Bodo, Dogri, Gujarati, Hindi, Kannada, Kashmiri, Konkani, Maithili, Malayalam, Manipuri, Marathi, Nepali, Odia, Punjabi, Sanskrit, Santali, Sindhi, Tamil, Telugu, Urdu — plus English and Hinglish code-mixing.

---

## 📝 License

MIT License — free to use, modify, and distribute.
