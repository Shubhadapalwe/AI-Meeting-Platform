import { useState, useEffect, useCallback } from "react";
import { transcribeMeeting, diarizeMeeting, getTranscripts } from "../services/api";

const SPEAKER_COLORS = [
  "#38bdf8", "#a78bfa", "#fb923c", "#34d399", "#f472b6",
  "#fbbf24", "#60a5fa", "#e879f9",
];

function getSpeakerColor(name) {
  if (!name) return "#94a3b8";
  let hash = 0;
  for (let i = 0; i < name.length; i++) hash = name.charCodeAt(i) + ((hash << 5) - hash);
  return SPEAKER_COLORS[Math.abs(hash) % SPEAKER_COLORS.length];
}

export default function TranscriptPanel({ meetingId }) {
  const [loading,    setLoading]    = useState(false);
  const [transcript, setTranscript] = useState(null);
  const [status,     setStatus]     = useState(
    "No transcript yet. Record audio then click Generate Transcript."
  );
  const [pendingRefresh, setPendingRefresh] = useState(false);

  // ── Auto-run transcription ─────────────────────────────────────────────────
  const runTranscribe = useCallback(async (silent = false) => {
    if (loading) return;
    try {
      setLoading(true);
      if (!silent) setStatus("Transcribing with Whisper… (may take 1–2 min)");
      else         setStatus("New recording detected — updating transcript…");
      await transcribeMeeting(meetingId);
      setStatus("Merging speaker segments…");
      const diarized = await diarizeMeeting(meetingId);
      setTranscript(diarized.transcript);
      setPendingRefresh(false);
      setStatus("✅ Transcript ready with speaker labels.");
    } catch (err) {
      setStatus("❌ " + (err.message || "Transcription failed. Check backend logs."));
    } finally {
      setLoading(false);
    }
  }, [meetingId, loading]);

  // ── Listen for new recordings uploaded on this device ─────────────────────
  useEffect(() => {
    function onUploaded(e) {
      if (e.detail?.meetingId !== meetingId) return;
      // Auto re-run transcription so display never stays stale
      setPendingRefresh(true);
      runTranscribe(true);
    }
    window.addEventListener("recording-uploaded", onUploaded);
    return () => window.removeEventListener("recording-uploaded", onUploaded);
  }, [meetingId, runTranscribe]);

  async function handleDiarize() {
    try {
      setLoading(true);
      setStatus("Re-identifying speakers…");
      const result = await diarizeMeeting(meetingId);
      setTranscript(result.transcript);
      setStatus("✅ Speaker diarization complete.");
    } catch (err) {
      setStatus("❌ " + (err.message || "Diarization failed. Generate transcript first."));
    } finally {
      setLoading(false);
    }
  }

  async function handleLoadTranscript() {
    try {
      setLoading(true);
      setStatus("Loading saved transcript…");
      try {
        const result = await diarizeMeeting(meetingId);
        setTranscript(result.transcript);
        setStatus("✅ Transcript loaded with speaker labels.");
        return;
      } catch (_) {}
      const result = await getTranscripts(meetingId);
      const list = result.transcripts || [];
      if (!list.length) { setStatus("No saved transcript found."); setTranscript(null); return; }
      setTranscript(list[list.length - 1]);
      setStatus("✅ Saved transcript loaded.");
    } catch (err) {
      setStatus("❌ Could not load transcript.");
    } finally {
      setLoading(false);
    }
  }

  const btnPrimary = {
    padding: "9px 14px", borderRadius: "12px", border: "none",
    cursor: loading ? "not-allowed" : "pointer", fontWeight: 800,
    background: "#2563eb", color: "white", opacity: loading ? 0.6 : 1,
  };
  const btnSecondary = {
    padding: "9px 14px", borderRadius: "12px",
    border: "1px solid rgba(255,255,255,0.15)", background: "transparent",
    color: "#e5e7eb", cursor: loading ? "not-allowed" : "pointer",
    fontWeight: 800, opacity: loading ? 0.6 : 1,
  };

  const speakerList      = transcript?.participants || transcript?.speakers || [];
  const oneSpeakerWarning = transcript && speakerList.length < 2;

  return (
    <div style={{
      background: "#0f172a", color: "#e5e7eb",
      border: "1px solid rgba(255,255,255,0.08)", borderRadius: "18px",
      padding: "16px", marginTop: "16px",
    }}>
      <h3 style={{ marginTop: 0, fontSize: 15 }}>🎙 AI Transcript</h3>

      <div style={{ display: "flex", gap: "8px", marginBottom: "12px", flexWrap: "wrap" }}>
        <button onClick={() => runTranscribe(false)} disabled={loading} style={btnPrimary}>
          {loading ? "Processing…" : "Generate Transcript"}
        </button>
        <button onClick={handleDiarize} disabled={loading} style={btnPrimary}>
          Identify Speakers
        </button>
        <button onClick={handleLoadTranscript} disabled={loading} style={btnSecondary}>
          Load Saved
        </button>
      </div>

      <p style={{ color: "#94a3b8", fontSize: "12px", margin: "0 0 10px" }}>{status}</p>

      {oneSpeakerWarning && (
        <div style={{
          background: "rgba(245,158,11,0.1)", border: "1px solid rgba(245,158,11,0.3)",
          borderRadius: 12, padding: "10px 14px", marginBottom: 12,
          color: "#fde68a", fontSize: 12,
        }}>
          <strong>⚠ Only one speaker detected.</strong>{" "}
          For two-speaker transcripts, <strong>both participants must click "⏺ Start Recording"</strong>{" "}
          on their own device before speaking. Then click <strong>Generate Transcript</strong> again.
        </div>
      )}

      {transcript && (
        <div>
          <div style={{ display: "flex", gap: "12px", fontSize: "12px", color: "#38bdf8", marginBottom: "10px", flexWrap: "wrap" }}>
            <span>🌐 {transcript.language}</span>
            <span>⏱ {transcript.duration}s</span>
            {speakerList.length > 0 && <span>👥 {speakerList.join(", ")}</span>}
          </div>

          <div style={{ maxHeight: "280px", overflowY: "auto" }}>
            {(transcript.segments || []).map((segment, index) => (
              <div key={index} style={{
                padding: "8px 0", borderBottom: "1px solid rgba(255,255,255,0.06)",
              }}>
                <div style={{ display: "flex", gap: "8px", alignItems: "center", marginBottom: "2px" }}>
                  <span style={{ color: "#4b5563", fontSize: "11px" }}>{segment.start}s</span>
                  {segment.speaker && (
                    <span style={{
                      color: getSpeakerColor(segment.speaker),
                      fontSize: "11px", fontWeight: 700,
                      background: getSpeakerColor(segment.speaker) + "22",
                      padding: "2px 8px", borderRadius: "99px",
                    }}>
                      {segment.speaker}
                    </span>
                  )}
                </div>
                <p style={{ margin: "0", fontSize: "13px" }}>{segment.text}</p>
              </div>
            ))}
          </div>
        </div>
      )}
    </div>
  );
}
