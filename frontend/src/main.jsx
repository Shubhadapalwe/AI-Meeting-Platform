import React, { useEffect, useMemo, useState } from "react";
import { createRoot } from "react-dom/client";
import RecordingControls from "./components/RecordingControls";
import TranscriptPanel from "./components/TranscriptPanel";
import AISummaryPanel from "./components/AISummaryPanel";
import AskAIPanel from "./components/AskAIPanel";
import MeetingHistory from "./pages/MeetingHistory";
import {
  LiveKitRoom,
  RoomAudioRenderer,
  VideoTrack,
  useParticipants,
  useTracks,
  useLocalParticipant,
  useConnectionState,
  useIsSpeaking,
} from "@livekit/components-react";
import "@livekit/components-styles";
import { Track, ConnectionState } from "livekit-client";
import {
  Video,
  Users,
  MessageSquare,
  FileText,
  Sparkles,
  Plus,
  Mic,
  MicOff,
  Camera,
  CameraOff,
  MonitorUp,
  PhoneOff,
  Copy,
  Wifi,
  Activity,
} from "lucide-react";
import "./styles.css";
import {
  createMeeting,
  createLiveKitToken,
  recordParticipantEvent,
} from "./services/api";

function App() {
  const initialMeetingId = window.location.pathname.startsWith("/meeting/")
    ? window.location.pathname.split("/meeting/")[1]
    : "";

  const [screen, setScreen] = useState(initialMeetingId ? "join" : "dashboard");
  const [meeting, setMeeting] = useState(
    initialMeetingId
      ? { meeting_id: initialMeetingId, title: "Direct Join Meeting" }
      : null
  );
  const [title, setTitle] = useState("MSC Project Discussion");
  const [hostName, setHostName] = useState("Shubhada");
  const [participantName, setParticipantName] = useState(
    initialMeetingId ? "Guest" : hostName
  );
  const [connection, setConnection] = useState(null);
  const [error, setError] = useState("");
  const [isCreating, setIsCreating] = useState(false);

  async function handleCreateMeeting() {
    try {
      setIsCreating(true);
      setError("");
      const data = await createMeeting({ title, host_name: hostName });
      setMeeting(data);
      setParticipantName(hostName);
      window.history.pushState({}, "", `/meeting/${data.meeting_id}`);
      setScreen("join");
    } catch (err) {
      setError(err.message || "Meeting creation failed");
    } finally {
      setIsCreating(false);
    }
  }

  async function handleJoinRoom(name) {
    try {
      setError("");
      const roomName = `meeting-${meeting.meeting_id}`;
      const data = await createLiveKitToken({
        room_name: roomName,
        participant_name: name,
      });
      setConnection(data);
      setParticipantName(name);
      setScreen("meeting");

      await recordParticipantEvent({
        meeting_id: meeting.meeting_id,
        participant_name: name,
        event_type: "joined",
      });
    } catch (err) {
      setError(err.message || "Unable to join LiveKit room");
    }
  }

  function leaveToDashboard() {
    setConnection(null);
    setScreen("dashboard");
    window.history.pushState({}, "", "/");
  }

  if (screen === "history") {
    return (
      <MeetingHistory
        onBack={leaveToDashboard}
        onJoin={(m) => {
          setMeeting(m);
          setParticipantName("Guest");
          setScreen("join");
        }}
      />
    );
  }

  if (screen === "meeting" && connection) {
    return (
      <MeetingRoom
        meeting={meeting}
        connection={connection}
        participantName={participantName}
        onLeave={leaveToDashboard}
      />
    );
  }

  if (screen === "join") {
    return (
      <JoinScreen
        meeting={meeting}
        defaultName={participantName}
        onJoin={handleJoinRoom}
        onBack={leaveToDashboard}
        error={error}
      />
    );
  }

  return (
    <main className="home-page">
      <div className="home-container">
        <p className="brand">AI Meeting Intelligence Platform</p>

        <section className="hero-card">
          <div>
            <h1>Zoom-like meetings with Fathom-style AI notes.</h1>
            <p>
              Phase 2 adds real WebRTC room joining, LiveKit tokens, participant
              state, mic/camera controls and active-speaker groundwork.
            </p>
          </div>

          <div className="hero-icon">
            <Sparkles size={48} />
          </div>
        </section>

        {error && <div className="error-box">{error}</div>}

        <section className="dashboard-grid">
          <div className="card create-card">
            <h2>Create Meeting</h2>

            <div className="form-grid">
              <label>
                Meeting Title
                <input
                  value={title}
                  onChange={(e) => setTitle(e.target.value)}
                />
              </label>

              <label>
                Host Name
                <input
                  value={hostName}
                  onChange={(e) => setHostName(e.target.value)}
                />
              </label>
            </div>

            <button
              className="primary-btn"
              onClick={handleCreateMeeting}
              disabled={isCreating}
            >
              <Plus size={18} />
              {isCreating ? "Creating..." : "Create Room"}
            </button>

            <button
              className="secondary-btn"
              onClick={() => setScreen("history")}
              style={{ marginTop: 10, width: "100%" }}
            >
              <FileText size={16} /> Meeting History
            </button>
          </div>

          <div className="card modules-card">
            <h2>Platform Features</h2>

            <Feature
              icon={<Activity />}
              title="Whisper Transcription"
              text="Accurate timestamped transcription via faster-whisper."
            />
            <Feature
              icon={<Users />}
              title="Speaker Diarization"
              text="Identifies who said what using LiveKit speaker events."
            />
            <Feature
              icon={<Sparkles />}
              title="AI Summary & Ask AI"
              text="Meeting summary, action items, and Q&A over your transcript."
            />
            <Feature
              icon={<MessageSquare />}
              title="Meeting Archive"
              text="Full-text search across all your meeting transcripts."
            />
          </div>
        </section>
      </div>
    </main>
  );
}

function JoinScreen({ meeting, defaultName, onJoin, onBack, error }) {
  const [name, setName] = useState(
    defaultName === "Guest" ? "" : defaultName || ""
  );
  const canJoin = name.trim().length > 0;
  // If host is on localhost, replace with the backend's known public IP
  // so the copied link works on Android (which can't resolve "localhost").
  const joinUrl = `${window.location.protocol}//${window.location.host}/meeting/${meeting?.meeting_id}`;

  async function copyLink() {
    await navigator.clipboard.writeText(joinUrl);
  }

  return (
    <main className="home-page">
      <div className="home-container narrow">
        <section className="card join-card">
          <p className="brand">Ready to Join</p>
          <h1>{meeting?.title || "Meeting Room"}</h1>
          <p className="join-url">Meeting ID: {meeting?.meeting_id}</p>

          {error && <div className="error-box">{error}</div>}

          <label>
            Your Display Name
            <input
              value={name}
              onChange={(e) => setName(e.target.value)}
              placeholder="Enter name e.g. Teacher / Priya / Rahul"
              autoFocus
            />
          </label>

          <div className="share-box">
            <span>{joinUrl}</span>
            <button onClick={copyLink}>
              <Copy size={16} /> Copy Link
            </button>
          </div>

          <div className="join-actions">
            <button
              className="primary-btn"
              disabled={!canJoin}
              onClick={() => onJoin(name.trim())}
            >
              <Video size={18} /> Join Meeting
            </button>

            <button className="secondary-btn" onClick={onBack}>
              Back
            </button>
          </div>

          <div className="info-box">
            Start LiveKit before joining. For local development, Docker Compose
            already includes a LiveKit server on port 7880.
          </div>
        </section>
      </div>
    </main>
  );
}

function MeetingRoom({ meeting, connection, participantName, onLeave }) {
  async function handleDisconnected() {
    await recordParticipantEvent({
      meeting_id: meeting.meeting_id,
      participant_name: participantName,
      event_type: "left",
    }).catch(() => null);
  }

  return (
    <LiveKitRoom
      token={connection.token}
      serverUrl={connection.url}
      connect={true}
      video={false}
      audio={false}
      onDisconnected={handleDisconnected}
      connectOptions={{ autoSubscribe: true }}
      style={{ width: "100%", height: "100%" }}
    >
      <RealMeetingShell
        meeting={meeting}
        participantName={participantName}
        onLeave={onLeave}
      />
      <RoomAudioRenderer />
    </LiveKitRoom>
  );
}

function RealMeetingShell({ meeting, participantName, onLeave }) {
  return (
    <div
      style={{
        width: "100vw",
        height: "100vh",
        display: "flex",
        flexDirection: "column",
        background: "#0f1117",
        overflow: "hidden",
      }}
    >
      <div
        style={{
          flexShrink: 0,
          display: "flex",
          alignItems: "center",
          justifyContent: "space-between",
          padding: "12px 24px",
          borderBottom: "1px solid rgba(255,255,255,0.08)",
        }}
      >
        <div style={{ display: "flex", alignItems: "center", gap: 16 }}>
          <ConnectionBadge />
          <span style={{ color: "#94a3b8", fontSize: 14, fontWeight: 600 }}>
            {meeting?.title || "Meeting"} · {participantName}
          </span>
        </div>

        <button
          onClick={onLeave}
          style={{
            display: "flex",
            alignItems: "center",
            gap: 8,
            background: "#fee2e2",
            color: "#b91c1c",
            border: "none",
            borderRadius: 12,
            padding: "10px 20px",
            fontWeight: 800,
            cursor: "pointer",
          }}
        >
          <PhoneOff size={16} /> Leave
        </button>
      </div>

      <div
        style={{
          flex: 1,
          minHeight: 0,
          display: "flex",
          gap: 0,
          overflow: "hidden",
        }}
      >
        <div
          style={{
            flex: 1,
            minWidth: 0,
            display: "flex",
            flexDirection: "column",
            padding: "16px",
            gap: 12,
            overflow: "hidden",
          }}
        >
          <VideoGrid meetingId={meeting.meeting_id} />

          <ControlsBar
            meetingId={meeting.meeting_id}
            participantName={participantName}
          />
        </div>

        <div
          style={{
            width: 360,
            flexShrink: 0,
            borderLeft: "1px solid rgba(255,255,255,0.08)",
            overflowY: "auto",
            background: "#161b27",
          }}
        >
          <SidePanel meetingId={meeting.meeting_id} />
        </div>
      </div>
    </div>
  );
}

function ConnectionBadge() {
  const connectionState = useConnectionState();
  const isConnected = connectionState === ConnectionState.Connected;

  return (
    <div
      style={{
        display: "inline-flex",
        alignItems: "center",
        gap: 8,
        padding: "6px 14px",
        borderRadius: 999,
        background: isConnected ? "#ecfdf5" : "#fff7ed",
        color: isConnected ? "#047857" : "#9a3412",
        border: `1px solid ${isConnected ? "#a7f3d0" : "#fed7aa"}`,
        fontWeight: 800,
        fontSize: 13,
      }}
    >
      <Wifi size={14} />
      {isConnected ? "Connected to LiveKit room" : `Connecting: ${connectionState}`}
    </div>
  );
}

function VideoGrid({ meetingId }) {
  const tracks = useTracks(
    [
      { source: Track.Source.Camera, withPlaceholder: true },
      { source: Track.Source.ScreenShare, withPlaceholder: false },
    ],
    { onlySubscribed: false }
  );

  const visibleTracks = useMemo(() => tracks.filter(Boolean), [tracks]);
  const count = visibleTracks.length;

  const getGridCols = () => {
    if (count <= 1) return "1fr";
    if (count <= 4) return "1fr 1fr";
    if (count <= 6) return "1fr 1fr 1fr";
    return "repeat(4, 1fr)";
  };

  return (
    <div
      style={{
        flex: 1,
        minHeight: 0,
        display: "grid",
        gridTemplateColumns: getGridCols(),
        gridAutoRows: "1fr",
        gap: 12,
      }}
    >
      {count === 0 && (
        <div
          style={{
            gridColumn: "1 / -1",
            display: "flex",
            alignItems: "center",
            justifyContent: "center",
            background: "#1e293b",
            borderRadius: 18,
            color: "#64748b",
            fontWeight: 700,
            fontSize: 16,
          }}
        >
          Waiting for participants...
        </div>
      )}

      {visibleTracks.map((trackRef) => (
        <ParticipantTile
          key={`${trackRef.participant.identity}-${trackRef.source}`}
          trackRef={trackRef}
          meetingId={meetingId}
        />
      ))}
    </div>
  );
}

function ParticipantTile({ trackRef, meetingId }) {
  const participant = trackRef.participant;
  // useIsSpeaking is a reactive hook — it re-renders whenever the speaking
  // state changes, so the useEffect below actually fires correctly.
  const isSpeaking = useIsSpeaking(participant);
  const label =
    trackRef.source === Track.Source.ScreenShare
      ? `${participant.name || participant.identity} — Screen`
      : participant.name || participant.identity;

  useEffect(() => {
    if (!isSpeaking) return;

    recordParticipantEvent({
      meeting_id: meetingId,
      participant_name: participant.name || participant.identity,
      event_type: "active_speaker",
      speaker_score: 1,
    }).catch(() => null);
  }, [isSpeaking, meetingId, participant.identity, participant.name]);

  return (
    <div
      style={{
        position: "relative",
        width: "100%",
        height: "100%",
        minHeight: 0,
        background: "#17233f",
        borderRadius: 18,
        overflow: "hidden",
        outline: isSpeaking ? "3px solid #22c55e" : "3px solid transparent",
        outlineOffset: "-3px",
        transition: "outline-color 0.2s",
      }}
    >
      {trackRef.publication && trackRef.publication.isSubscribed ? (
        <VideoTrack
          trackRef={trackRef}
          style={{
            width: "100%",
            height: "100%",
            objectFit: "cover",
            position: "absolute",
            inset: 0,
          }}
        />
      ) : (
        <div
          style={{
            width: "100%",
            height: "100%",
            display: "flex",
            alignItems: "center",
            justifyContent: "center",
          }}
        >
          <div
            style={{
              width: 72,
              height: 72,
              borderRadius: "50%",
              background: "rgba(255,255,255,0.12)",
              display: "flex",
              alignItems: "center",
              justifyContent: "center",
              fontSize: 30,
              fontWeight: 900,
              color: "white",
            }}
          >
            {(participant.name || participant.identity || "?")
              .slice(0, 1)
              .toUpperCase()}
          </div>
        </div>
      )}

      <span
        style={{
          position: "absolute",
          left: 14,
          bottom: 14,
          background: "rgba(15,23,42,0.75)",
          color: "white",
          padding: "6px 12px",
          borderRadius: 999,
          fontWeight: 700,
          fontSize: 13,
          maxWidth: "calc(100% - 28px)",
          overflow: "hidden",
          textOverflow: "ellipsis",
          whiteSpace: "nowrap",
        }}
      >
        {label}
      </span>

      {isSpeaking && (
        <small
          style={{
            position: "absolute",
            right: 14,
            top: 14,
            background: "#22c55e",
            color: "#052e16",
            padding: "5px 10px",
            borderRadius: 999,
            fontWeight: 900,
            fontSize: 11,
          }}
        >
          Speaking
        </small>
      )}
    </div>
  );
}

function ControlsBar({ meetingId, participantName }) {
  const {
    localParticipant,
    isMicrophoneEnabled,
    isCameraEnabled,
    isScreenShareEnabled,
  } = useLocalParticipant();
  const [mediaError, setMediaError] = useState("");

  async function toggleMic() {
    try {
      setMediaError("");
      const next = !isMicrophoneEnabled;
      await localParticipant.setMicrophoneEnabled(next);
      await recordParticipantEvent({
        meeting_id: meetingId,
        participant_name: participantName,
        event_type: "mic_changed",
        is_muted: !next,
      });
    } catch (e) {
      if (!navigator.mediaDevices) {
        setMediaError("Mic blocked: HTTPS required. Open about:config in Firefox → set media.devices.insecure.enabled = true");
      } else {
        setMediaError("Mic error: " + (e.message || e.name));
      }
    }
  }

  async function toggleCamera() {
    try {
      setMediaError("");
      const next = !isCameraEnabled;
      await localParticipant.setCameraEnabled(next);
      await recordParticipantEvent({
        meeting_id: meetingId,
        participant_name: participantName,
        event_type: "camera_changed",
        is_camera_on: next,
      });
    } catch (e) {
      if (!navigator.mediaDevices) {
        setMediaError("Camera blocked: HTTPS required. Open about:config in Firefox → set media.devices.insecure.enabled = true");
      } else {
        setMediaError("Camera error: " + (e.message || e.name));
      }
    }
  }

  async function toggleScreen() {
    const next = !isScreenShareEnabled;
    await localParticipant.setScreenShareEnabled(next);
    await recordParticipantEvent({
      meeting_id: meetingId,
      participant_name: participantName,
      event_type: "screen_share_changed",
      is_screen_sharing: next,
    });
  }

  const btnStyle = (active) => ({
    display: "inline-flex",
    alignItems: "center",
    gap: 8,
    padding: "10px 22px",
    borderRadius: 14,
    border: "none",
    background: active ? "rgba(255,255,255,0.1)" : "rgba(239,68,68,0.2)",
    color: active ? "#e2e8f0" : "#fca5a5",
    fontWeight: 800,
    cursor: "pointer",
    fontSize: 14,
  });

  return (
    <div style={{ flexShrink: 0 }}>
      {mediaError && (
        <div style={{
          background: "#7f1d1d", color: "#fecaca", fontSize: 12, fontWeight: 600,
          padding: "8px 16px", borderRadius: 10, marginBottom: 8, textAlign: "center",
        }}>
          ⚠️ {mediaError}
        </div>
      )}
    <div
      style={{
        display: "flex",
        alignItems: "center",
        justifyContent: "center",
        gap: 12,
        padding: "10px 0",
      }}
    >
      <button onClick={toggleMic} style={btnStyle(isMicrophoneEnabled)}>
        {isMicrophoneEnabled ? <Mic size={18} /> : <MicOff size={18} />}
        {isMicrophoneEnabled ? "Mute" : "Unmute"}
      </button>

      <button onClick={toggleCamera} style={btnStyle(isCameraEnabled)}>
        {isCameraEnabled ? <Camera size={18} /> : <CameraOff size={18} />}
        {isCameraEnabled ? "Camera Off" : "Camera On"}
      </button>

      <button onClick={toggleScreen} style={btnStyle(!isScreenShareEnabled)}>
        <MonitorUp size={18} />
        {isScreenShareEnabled ? "Stop Share" : "Share Screen"}
      </button>

      <RecordingControls
        meetingId={meetingId}
        participantName={participantName}
      />
    </div>
    </div>
  );
}

function SidePanel({ meetingId }) {
  const participants = useParticipants();
  const [activeTab, setActiveTab] = useState("transcript");

  const sectionTitle = (icon, text) => (
    <div
      style={{
        display: "flex",
        alignItems: "center",
        gap: 8,
        margin: "20px 0 10px",
        padding: "0 20px",
      }}
    >
      <span style={{ color: "#6d8cff" }}>{icon}</span>
      <h3 style={{ margin: 0, fontSize: 15, color: "#e2e8f0", fontWeight: 700 }}>
        {text}
      </h3>
    </div>
  );

  return (
    <div style={{ padding: "8px 0" }}>
      {sectionTitle(<Users size={16} />, `Participants (${participants.length})`)}

      <div
        style={{
          display: "flex",
          flexDirection: "column",
          gap: 8,
          padding: "0 16px",
        }}
      >
        {participants.map((p) => (
          <div
            key={p.identity}
            style={{
              display: "flex",
              alignItems: "center",
              justifyContent: "space-between",
              background: "rgba(255,255,255,0.05)",
              borderRadius: 12,
              padding: "10px 14px",
            }}
          >
            <strong style={{ color: "#e2e8f0", fontSize: 14 }}>
              {p.name || p.identity}
            </strong>
            <small
              style={{
                color: p.isSpeaking ? "#4ade80" : "#64748b",
                fontWeight: 700,
                fontSize: 12,
              }}
            >
              {p.isSpeaking ? "Speaking" : "Connected"}
            </small>
          </div>
        ))}
      </div>

      {/* AI Tabs */}
      <div style={{
        display: "flex", gap: 4, padding: "8px 16px 0", marginTop: 8,
        borderTop: "1px solid rgba(255,255,255,0.07)",
      }}>
        {["transcript", "summary", "ask"].map((tab) => (
          <button
            key={tab}
            onClick={() => setActiveTab(tab)}
            style={{
              flex: 1, padding: "8px 4px", borderRadius: 10, border: "none",
              background: activeTab === tab ? "#2563eb" : "rgba(255,255,255,0.06)",
              color: activeTab === tab ? "white" : "#94a3b8",
              fontWeight: 700, fontSize: 11, cursor: "pointer",
              textTransform: "capitalize",
            }}
          >
            {tab === "transcript" ? "📝 Transcript" : tab === "summary" ? "✨ Summary" : "💬 Ask AI"}
          </button>
        ))}
      </div>

      <div style={{ padding: "8px 0 16px" }}>
        {activeTab === "transcript" && <TranscriptPanel meetingId={meetingId} />}
        {activeTab === "summary" && <AISummaryPanel meetingId={meetingId} />}
        {activeTab === "ask" && <AskAIPanel meetingId={meetingId} />}
      </div>
    </div>
  );
}

function Feature({ icon, title, text }) {
  return (
    <div className="feature">
      <div className="feature-icon">{icon}</div>
      <div>
        <strong>{title}</strong>
        <p>{text}</p>
      </div>
    </div>
  );
}

createRoot(document.getElementById("root")).render(<App />);