import { useEffect, useRef, useState } from 'react'

export default function ParticipantTile({ participant, isSpeaking }) {
  const videoRef = useRef(null)
  const [hasVideo, setHasVideo] = useState(false)

  useEffect(() => {
    let attachedTrack = null

    participant.videoTrackPublications.forEach((publication) => {
      if (publication.track && videoRef.current) {
        publication.track.attach(videoRef.current)
        attachedTrack = publication.track
        setHasVideo(true)
      }
    })

    return () => {
      if (attachedTrack) {
        attachedTrack.detach()
      }
    }
  }, [participant])

  const initial = participant.identity?.charAt(0)?.toUpperCase() || '?'

  return (
    <div style={{
      position: 'relative',
      width: '100%',
      height: '100%',
      minHeight: 0,
      background: '#111827',
      borderRadius: '16px',
      overflow: 'hidden',
      outline: isSpeaking ? '2px solid #22c55e' : '2px solid transparent',
      outlineOffset: '-2px',
      transition: 'outline-color 0.2s ease',
    }}>
      {hasVideo ? (
        <video
          ref={videoRef}
          autoPlay
          playsInline
          muted={participant.isLocal}
          style={{
            width: '100%',
            height: '100%',
            objectFit: 'cover',
            display: 'block',
          }}
        />
      ) : (
        <div style={{
          width: '100%',
          height: '100%',
          display: 'flex',
          alignItems: 'center',
          justifyContent: 'center',
          background: '#1e293b',
        }}>
          <div style={{
            width: '72px',
            height: '72px',
            borderRadius: '50%',
            background: '#334155',
            display: 'flex',
            alignItems: 'center',
            justifyContent: 'center',
            fontSize: '28px',
            fontWeight: '600',
            color: '#e2e8f0',
            letterSpacing: '-0.5px',
          }}>
            {initial}
          </div>
        </div>
      )}

      {isSpeaking && (
        <div style={{
          position: 'absolute',
          top: '12px',
          right: '12px',
          background: '#22c55e',
          color: '#fff',
          fontSize: '11px',
          fontWeight: '600',
          padding: '3px 8px',
          borderRadius: '999px',
          letterSpacing: '0.04em',
          textTransform: 'uppercase',
        }}>
          Speaking
        </div>
      )}

      <div style={{
        position: 'absolute',
        bottom: '12px',
        left: '12px',
        background: 'rgba(0,0,0,0.55)',
        backdropFilter: 'blur(6px)',
        color: '#f1f5f9',
        fontSize: '13px',
        fontWeight: '500',
        padding: '5px 12px',
        borderRadius: '999px',
        maxWidth: 'calc(100% - 24px)',
        overflow: 'hidden',
        textOverflow: 'ellipsis',
        whiteSpace: 'nowrap',
      }}>
        {participant.identity}
        {participant.isLocal && (
          <span style={{ marginLeft: '6px', opacity: 0.6, fontSize: '11px' }}>
            (You)
          </span>
        )}
      </div>
    </div>
  )
}
