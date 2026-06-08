import { useRef, useState } from "react";

import { uploadRecording, recordParticipantEvent } from "../services/api";

export default function RecordingControls({ meetingId, participantName, onRecordingStarted }) {
  const recorderRef = useRef(null);
  const streamRef = useRef(null);
  const chunksRef = useRef([]);

  const [isRecording, setIsRecording] = useState(false);
  const [status, setStatus] = useState("Not recording");
  const [uploading, setUploading] = useState(false);

async function startRecording() {
  try {
    // Android Chrome does not support getDisplayMedia — fall back to mic only.
    const hasDisplayMedia =
      typeof navigator.mediaDevices?.getDisplayMedia === "function";

    let combinedStream;

    if (hasDisplayMedia) {
      // Desktop: capture screen (video + system audio) + microphone
      const screenStream = await navigator.mediaDevices.getDisplayMedia({
        video: true,
        audio: true,
      });
      const micStream = await navigator.mediaDevices.getUserMedia({
        audio: true,
      });
      combinedStream = new MediaStream([
        ...screenStream.getVideoTracks(),
        ...screenStream.getAudioTracks(),
        ...micStream.getAudioTracks(),
      ]);
    } else {
      // Mobile (Android): capture microphone only
      combinedStream = await navigator.mediaDevices.getUserMedia({
        audio: true,
        video: false,
      });
    }

    streamRef.current = combinedStream;
    chunksRef.current = [];

    // Pick a MIME type supported by the current browser/platform
    const mimeType = [
      "video/webm;codecs=vp8,opus",
      "video/webm",
      "audio/webm;codecs=opus",
      "audio/webm",
    ].find((t) => MediaRecorder.isTypeSupported(t)) || "";

    const recorder = new MediaRecorder(combinedStream, {
      ...(mimeType ? { mimeType } : {}),
    });

    recorder.ondataavailable = (event) => {
      if (event.data && event.data.size > 0) {
        chunksRef.current.push(event.data);
      }
    };

    recorder.onstop = async () => {
      const blob = new Blob(chunksRef.current, {
        type: "video/webm",
      });

      setUploading(true);
      setStatus("Uploading recording...");

      try {
        await uploadRecording({
          meetingId,
          participantName,
          blob,
        });

        setStatus("Recording saved. Audio ready for Whisper.");
      } catch (error) {
        console.error(error);
        setStatus("Upload failed. Check backend logs.");
      } finally {
        setUploading(false);

        combinedStream.getTracks().forEach((track) => track.stop());
      }
    };

    recorderRef.current = recorder;
    recorder.start(1000);

    // Emit a timestamped event so the backend can anchor the audio timeline
    // to the exact moment recording started (not the earlier join time).
    await recordParticipantEvent({
      meeting_id: meetingId,
      participant_name: participantName,
      event_type: "recording_started",
    }).catch(() => null);

    setIsRecording(true);
    setStatus(hasDisplayMedia ? "Recording screen + mic..." : "Recording mic only (mobile)...");
  } catch (error) {
    console.error(error);
    setStatus(
      error.name === "NotAllowedError"
        ? "Microphone permission denied. Allow mic access and try again."
        : "Recording failed: " + error.message
    );
  }
}

  function stopRecording() {
    if (!recorderRef.current) return;

    recorderRef.current.stop();
    setIsRecording(false);
    setStatus("Recording stopped.");
  }

  const buttonStyle = {
    border: "none",
    borderRadius: 14,
    padding: "10px 18px",
    fontWeight: 900,
    cursor: uploading ? "not-allowed" : "pointer",
    background: isRecording ? "#dc2626" : "#16a34a",
    color: "white",
  };

  return (
    <div style={{ display: "flex", alignItems: "center", gap: 10 }}>
      {!isRecording ? (
        <button disabled={uploading} onClick={startRecording} style={buttonStyle}>
          ⏺ Start Recording
        </button>
      ) : (
        <button onClick={stopRecording} style={buttonStyle}>
          ⏹ Stop Recording
        </button>
      )}

      <span style={{ color: "#94a3b8", fontSize: 12, fontWeight: 700 }}>
        {status}
      </span>
    </div>
  );
}