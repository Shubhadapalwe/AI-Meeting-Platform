import { useRef, useState } from "react";
import { uploadRecording, recordParticipantEvent } from "../services/api";

/**
 * RecordingControls — clean dual-track recording
 *
 * ROOT CAUSE of echo + speaker confusion (now fixed):
 *   Two simultaneous getUserMedia calls on the same mic break Chrome's AEC
 *   context — teacher's voice bled into Shubhada's recording file.
 *
 * FIX: Reuse LiveKit's existing mic track (already AEC-processed) for the
 * mic recording. Only create a new getUserMedia if LiveKit hasn't enabled
 * the mic yet. This gives ONE mic consumer → clean AEC → clean speaker files.
 *
 * Dual-track approach:
 *   Track 1 – mic (LiveKit's AEC-processed track)  → participantName file
 *   Track 2 – system audio via getDisplayMedia      → otherParticipants[0] file
 */
export default function RecordingControls({
  meetingId,
  participantName,
  otherParticipants = [],
}) {
  const micRecorderRef = useRef(null);
  const sysRecorderRef = useRef(null);
  const micChunksRef   = useRef([]);
  const sysChunksRef   = useRef([]);
  const allTracksRef   = useRef([]);   // tracks WE created (to stop later)

  const [isRecording, setIsRecording] = useState(false);
  const [status,      setStatus]      = useState("Not recording");
  const [uploading,   setUploading]   = useState(false);

  // ── helpers ────────────────────────────────────────────────────────────────

  function pickMime(hasVideo) {
    if (hasVideo) {
      return (
        ["video/webm;codecs=vp8,opus", "video/webm;codecs=vp9,opus", "video/webm"]
          .find((t) => MediaRecorder.isTypeSupported(t)) || ""
      );
    }
    return (
      ["audio/webm;codecs=opus", "audio/webm", "audio/ogg;codecs=opus"]
        .find((t) => MediaRecorder.isTypeSupported(t)) || ""
    );
  }

  function makeRecorder(stream, chunks) {
    const hasVideo = stream.getVideoTracks().length > 0;
    const mime     = pickMime(hasVideo);
    const rec      = new MediaRecorder(stream, mime ? { mimeType: mime } : {});
    rec.ondataavailable = (e) => { if (e.data?.size > 0) chunks.push(e.data); };
    return rec;
  }

  async function upload(chunks, name, isVideo) {
    if (!chunks.length) return;
    const type = isVideo ? "video/webm" : "audio/webm";
    const blob = new Blob(chunks, { type });
    await uploadRecording({ meetingId, participantName: name, blob });
    window.dispatchEvent(
      new CustomEvent("recording-uploaded", { detail: { meetingId, participant: name } })
    );
  }

  // ── start recording ────────────────────────────────────────────────────────

  async function startRecording() {
    try {
      micChunksRef.current = [];
      sysChunksRef.current = [];
      allTracksRef.current = [];

      const AEC_CONSTRAINTS = {
        echoCancellation: true,
        noiseSuppression: true,
        autoGainControl: true,
      };

      // ── 1. Get mic audio (with full AEC) ────────────────────────────────
      const ownedMicStream = await navigator.mediaDevices.getUserMedia({ audio: AEC_CONSTRAINTS, video: false });
      allTracksRef.current.push(...ownedMicStream.getTracks());
      const micOnlyStream = new MediaStream(ownedMicStream.getAudioTracks());

      // ── 2. Get system audio (teacher's voice via LiveKit) ────────────────
      const hasDisplayMedia = typeof navigator.mediaDevices?.getDisplayMedia === "function";
      const remoteName      = otherParticipants[0];
      let sysAudioTrack     = null;

      if (hasDisplayMedia && remoteName) {
        try {
          // Ask user to share screen; audio:true captures system audio
          // (i.e. teacher's voice playing through speakers)
          const screenStream = await navigator.mediaDevices.getDisplayMedia({
            video: true,   // screen picker requires video:true on most browsers
            audio: true,
          });

          const sysAudioTracks = screenStream.getAudioTracks();
          // We don't need the screen video for transcription — stop it now
          // to avoid wasting resources and misleading the user
          screenStream.getVideoTracks().forEach((t) => {
            t.stop();
            allTracksRef.current.push(t);
          });

          if (sysAudioTracks.length > 0) {
            sysAudioTrack = sysAudioTracks[0];
            allTracksRef.current.push(sysAudioTrack);
          }
        } catch {
          // User cancelled screen picker → mic-only mode
        }
      }

      // ── 3. Set up recorders ──────────────────────────────────────────────
      const hasDual = !!sysAudioTrack && !!remoteName;

      // Mic recorder → Shubhada's file
      const micRec = makeRecorder(micOnlyStream, micChunksRef.current);
      micRec.onstop = async () => {
        setUploading(true);
        setStatus("Uploading…");
        try {
          await upload(micChunksRef.current, participantName, false);
          if (!hasDual) setStatus("✅ Saved. Click Generate Transcript.");
        } catch (e) {
          setStatus("Upload failed: " + e.message);
        } finally {
          if (!hasDual) setUploading(false);
        }
      };
      micRecorderRef.current = micRec;

      // System audio recorder → teacher's file
      if (hasDual) {
        const sysStream = new MediaStream([sysAudioTrack]);
        const sysRec    = makeRecorder(sysStream, sysChunksRef.current);
        sysRec.onstop   = async () => {
          try {
            await upload(sysChunksRef.current, remoteName, false);
            setStatus("✅ Both speakers saved. Click Generate Transcript.");
          } catch (e) {
            setStatus("Remote upload failed: " + e.message);
          } finally {
            setUploading(false);
          }
        };
        sysRecorderRef.current = sysRec;
        sysRec.start(1000);
      }

      micRec.start(1000);

      setStatus(
        hasDual
          ? `🎙 Recording ${participantName} (mic) + ${remoteName} (speakers)…`
          : "🎙 Recording mic only… (teacher should Record on their device)"
      );

      await recordParticipantEvent({
        meeting_id:       meetingId,
        participant_name: participantName,
        event_type:       "recording_started",
      }).catch(() => null);

      setIsRecording(true);
    } catch (error) {
      console.error("Recording error:", error);
      setStatus(
        error.name === "NotAllowedError"
          ? "Permission denied — allow mic access and try again."
          : "Recording failed: " + error.message
      );
    }
  }

  // ── stop recording ─────────────────────────────────────────────────────────

  function stopRecording() {
    if (micRecorderRef.current?.state !== "inactive") micRecorderRef.current?.stop();
    if (sysRecorderRef.current?.state !== "inactive") sysRecorderRef.current?.stop();
    // Only stop tracks WE created, not LiveKit's mic track
    allTracksRef.current.forEach((t) => t.stop());
    allTracksRef.current = [];
    sysRecorderRef.current = null;
    setIsRecording(false);
    if (!uploading) setStatus("Stopped — uploading…");
  }

  // ── render ─────────────────────────────────────────────────────────────────

  const btn = {
    border: "none", borderRadius: 14, padding: "10px 18px",
    fontWeight: 900, cursor: uploading ? "not-allowed" : "pointer",
    background: isRecording ? "#dc2626" : "#16a34a", color: "white",
  };

  return (
    <div style={{ display: "flex", alignItems: "center", gap: 10, flexWrap: "wrap" }}>
      {!isRecording ? (
        <button disabled={uploading} onClick={startRecording} style={btn}>
          ⏺ Start Recording
        </button>
      ) : (
        <button onClick={stopRecording} style={btn}>
          ⏹ Stop Recording
        </button>
      )}
      <span style={{ color: "#94a3b8", fontSize: 12, fontWeight: 700 }}>
        {status}
      </span>
    </div>
  );
}
