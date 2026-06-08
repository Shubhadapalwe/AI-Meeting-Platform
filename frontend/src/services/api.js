// Empty string = same origin. Vite proxies /api → backend:8000.
// This means no CORS issues on any browser or device.
const API_BASE = "";

export function getApiBase() {
  return API_BASE;
}

async function request(path, options = {}) {
  const response = await fetch(`${API_BASE}${path}`, {
    headers: {
      "Content-Type": "application/json",
      ...(options.headers || {}),
    },
    ...options,
  });

  if (!response.ok) {
    const detail = await response.text();
    throw new Error(detail || `Request failed: ${path}`);
  }

  return response.json();
}

export async function createMeeting(payload) {
  return request("/api/meetings/create", {
    method: "POST",
    body: JSON.stringify(payload),
  });
}

export async function getMeeting(meetingId) {
  return request(`/api/meetings/${meetingId}`);
}

export async function createLiveKitToken(payload) {
  return request("/api/livekit/token", {
    method: "POST",
    body: JSON.stringify(payload),
  });
}

export async function recordParticipantEvent(payload) {
  return request("/api/participants/events", {
    method: "POST",
    body: JSON.stringify(payload),
  });
}

export async function getParticipantEvents(meetingId) {
  return request(`/api/participants/events/${meetingId}`);
}

export async function getMockSummary(payload) {
  return request("/api/ai/mock-summary", {
    method: "POST",
    body: JSON.stringify(payload),
  });
}

export async function uploadRecording({ meetingId, participantName, blob }) {
  const formData = new FormData();

  formData.append("meeting_id", meetingId);
  formData.append("participant_name", participantName);
  formData.append("file", blob, `${meetingId}.webm`);

  const response = await fetch(`${API_BASE}/api/recordings/upload`, {
    method: "POST",
    body: formData,
  });

  if (!response.ok) {
    const detail = await response.text();
    throw new Error(detail || "Recording upload failed");
  }

  return response.json();
}

export async function transcribeMeeting(meetingId) {
  return request(`/api/transcripts/transcribe/${meetingId}`, {
    method: "POST",
  });
}

export async function getTranscripts(meetingId) {
  return request(`/api/transcripts/${meetingId}`);
}

export async function diarizeMeeting(meetingId) {
  return request(`/api/transcripts/diarize/${meetingId}`, {
    method: "POST",
  });
}

// Phase 6 — Real AI Summary
export async function generateAISummary(meetingId) {
  return request("/api/ai/summary", {
    method: "POST",
    body: JSON.stringify({ meeting_id: meetingId }),
  });
}

// Phase 7 — Ask AI
export async function askAI(meetingId, question) {
  return request("/api/ai/ask", {
    method: "POST",
    body: JSON.stringify({ meeting_id: meetingId, question }),
  });
}

// Phase 8 — Analytics
export async function getMeetingAnalytics(meetingId) {
  return request(`/api/ai/analytics/${meetingId}`);
}

// Phase 8 — Meeting history
export async function getMeetingHistory() {
  return request("/api/meetings/history");
}

// Phase 8 — Search transcripts
export async function searchTranscripts(query) {
  return request(`/api/meetings/search?q=${encodeURIComponent(query)}`);
}

// Phase 9 — Meeting Minutes PDF
export async function generateMeetingPDF(meetingId) {
  return request(`/api/pdf/generate/${meetingId}`, {
    method: "POST",
  });
}

export function getPDFDownloadUrl(downloadUrl) {
  return `${API_BASE}${downloadUrl}`;
}