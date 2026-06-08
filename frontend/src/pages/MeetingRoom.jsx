import ConnectionStatus from './ConnectionStatus'
import ControlsBar from './ControlsBar'
import ParticipantGrid from './ParticipantGrid'
import TranscriptPanel from '../components/TranscriptPanel'

export default function MeetingRoom({
  room,
  participants,
  connected,
  activeSpeaker,
  meetingId = 'demo_meeting_001',
}) {
  return (
    <div style={{
      width: '100vw',
      height: '100vh',
      display: 'flex',
      flexDirection: 'column',
      background: '#0a0a0f',
      overflow: 'auto',
    }}>
      <div style={{
        flexShrink: 0,
        padding: '12px 20px',
        display: 'flex',
        alignItems: 'center',
        justifyContent: 'space-between',
        borderBottom: '1px solid rgba(255,255,255,0.07)',
      }}>
        <ConnectionStatus connected={connected} />
      </div>

      <div style={{
        flex: 1,
        minHeight: 0,
        padding: '16px',
        overflow: 'auto',
      }}>
        <ParticipantGrid
          participants={participants}
          activeSpeaker={activeSpeaker}
        />
      </div>

      <div style={{ flexShrink: 0 }}>
        <ControlsBar room={room} />
      </div>

      <div style={{
        flexShrink: 0,
        padding: '0 16px 16px',
        maxHeight: '360px',
        overflowY: 'auto',
      }}>
        <TranscriptPanel meetingId={meetingId} />
      </div>
    </div>
  )
}