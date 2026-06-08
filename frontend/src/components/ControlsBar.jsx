import { useState } from 'react'
import RecordingControls from './RecordingControls'

export default function ControlsBar({ room }) {
  const [micOn, setMicOn] = useState(true)
  const [cameraOn, setCameraOn] = useState(true)
  const [sharing, setSharing] = useState(false)

  const toggleMic = async () => {
    if (!room) return
    const next = !micOn
    await room.localParticipant.setMicrophoneEnabled(next)
    setMicOn(next)
  }

  const toggleCamera = async () => {
    if (!room) return
    const next = !cameraOn
    await room.localParticipant.setCameraEnabled(next)
    setCameraOn(next)
  }

  const toggleScreenShare = async () => {
    if (!room) return
    const next = !sharing
    await room.localParticipant.setScreenShareEnabled(next)
    setSharing(next)
  }

  const btn = (active) => ({
    display: 'flex',
    alignItems: 'center',
    gap: '7px',
    padding: '10px 20px',
    borderRadius: '999px',
    border: 'none',
    cursor: 'pointer',
    fontSize: '14px',
    fontWeight: '500',
    background: active ? 'rgba(255,255,255,0.12)' : 'rgba(239,68,68,0.2)',
    color: active ? '#e2e8f0' : '#fca5a5',
  })

  return (
    <div style={{
      display: 'flex',
      alignItems: 'center',
      justifyContent: 'center',
      gap: '12px',
      padding: '16px 24px',
      borderTop: '1px solid rgba(255,255,255,0.07)',
    }}>
      <button onClick={toggleMic} style={btn(micOn)}>
        {micOn ? '🎤 Mute' : '🔇 Unmute'}
      </button>

      <button onClick={toggleCamera} style={btn(cameraOn)}>
        {cameraOn ? '📷 Camera Off' : '📷 Camera On'}
      </button>

      <button onClick={toggleScreenShare} style={btn(!sharing)}>
        {sharing ? '🖥 Stop Sharing' : '🖥 Share Screen'}
      </button>

      <RecordingControls
        meetingId="demo_meeting_001"
        participantName="local_user"
      />
    </div>
  )
}