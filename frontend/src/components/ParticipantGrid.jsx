import ParticipantTile from './ParticipantTile'

export default function ParticipantGrid({ participants, activeSpeaker }) {
  const count = participants.length

  const getGridTemplate = () => {
    if (count === 0) return { cols: '1fr', rows: '1fr' }
    if (count === 1) return { cols: '1fr', rows: '1fr' }
    if (count === 2) return { cols: '1fr 1fr', rows: '1fr' }
    if (count === 3) return { cols: '1fr 1fr 1fr', rows: '1fr' }
    if (count === 4) return { cols: '1fr 1fr', rows: '1fr 1fr' }
    if (count <= 6) return { cols: '1fr 1fr 1fr', rows: '1fr 1fr' }
    if (count <= 9) return { cols: '1fr 1fr 1fr', rows: '1fr 1fr 1fr' }
    return { cols: 'repeat(4, 1fr)', rows: 'repeat(auto-fill, 1fr)' }
  }

  const { cols, rows } = getGridTemplate()

  return (
    <div style={{
      width: '100%',
      height: '100%',
      display: 'grid',
      gridTemplateColumns: cols,
      gridTemplateRows: rows,
      gap: '10px',
      boxSizing: 'border-box',
    }}>
      {participants.map((participant) => (
        <ParticipantTile
          key={participant.identity}
          participant={participant}
          isSpeaking={activeSpeaker === participant.identity}
        />
      ))}
    </div>
  )
}
