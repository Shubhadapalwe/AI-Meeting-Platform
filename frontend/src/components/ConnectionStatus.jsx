export default function ConnectionStatus({ connected }) {
  return (
    <div style={{
      display: 'flex',
      alignItems: 'center',
      gap: '8px',
      fontSize: '13px',
      fontWeight: '500',
      color: connected ? '#4ade80' : '#94a3b8',
    }}>
      <div style={{
        width: '8px',
        height: '8px',
        borderRadius: '50%',
        background: connected ? '#22c55e' : '#64748b',
        boxShadow: connected ? '0 0 0 3px rgba(34,197,94,0.2)' : 'none',
        transition: 'all 0.3s ease',
      }} />
      {connected ? 'Connected' : 'Connecting…'}
    </div>
  )
}
