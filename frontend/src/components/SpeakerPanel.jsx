import { useEffect, useState } from "react";

const API_BASE = "";

const SPEAKER_COLORS = [
  "#3b82f6", "#10b981", "#f59e0b", "#ef4444",
  "#8b5cf6", "#ec4899", "#06b6d4", "#84cc16",
];

function getSpeakerColor(index) {
  return SPEAKER_COLORS[index % SPEAKER_COLORS.length];
}

function Bar({ pct, color }) {
  return (
    <div style={{ background: "rgba(255,255,255,0.06)", borderRadius: 4, height: 8, overflow: "hidden" }}>
      <div
        style={{
          width: `${Math.min(pct, 100)}%`,
          height: "100%",
          background: color,
          borderRadius: 4,
          transition: "width 0.5s ease",
        }}
      />
    </div>
  );
}

export default function SpeakerPanel({ meetingId }) {
  const [data, setData] = useState(null);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState(null);

  async function fetchAnalytics() {
    if (!meetingId) return;
    setLoading(true);
    setError(null);
    try {
      const res = await fetch(`${API_BASE}/api/speakers/${meetingId}`);
      if (!res.ok) {
        const detail = await res.text();
        throw new Error(detail || "Failed to load speaker analytics");
      }
      const json = await res.json();
      setData(json);
    } catch (err) {
      setError(err.message);
    } finally {
      setLoading(false);
    }
  }

  useEffect(() => {
    fetchAnalytics();
  }, [meetingId]);

  const card = {
    background: "rgba(255,255,255,0.04)",
    border: "1px solid rgba(255,255,255,0.08)",
    borderRadius: 14,
    padding: "14px 16px",
    marginBottom: 10,
  };

  const label = { fontSize: 11, color: "#6b7280", marginBottom: 2 };
  const value = { fontSize: 15, fontWeight: 700, color: "#e5e7eb" };

  return (
    <div style={{ color: "#e5e7eb", fontSize: 13 }}>
      {/* Header */}
      <div style={{ display: "flex", justifyContent: "space-between", alignItems: "center", marginBottom: 14 }}>
        <span style={{ fontWeight: 700, fontSize: 15 }}>🎙 Speaker Analytics</span>
        <button
          onClick={fetchAnalytics}
          disabled={loading}
          style={{
            background: "rgba(255,255,255,0.07)",
            border: "none",
            color: "#e5e7eb",
            borderRadius: 8,
            padding: "5px 12px",
            cursor: loading ? "not-allowed" : "pointer",
            fontSize: 12,
          }}
        >
          {loading ? "Loading…" : "↻ Refresh"}
        </button>
      </div>

      {/* Error state */}
      {error && (
        <div style={{ ...card, background: "rgba(239,68,68,0.08)", border: "1px solid rgba(239,68,68,0.2)", color: "#fca5a5" }}>
          {error}
        </div>
      )}

      {/* Empty state */}
      {!loading && !error && !data && (
        <div style={{ ...card, color: "#6b7280", textAlign: "center" }}>
          No analytics yet. Generate a transcript first.
        </div>
      )}

      {/* Summary row */}
      {data && (
        <>
          <div style={{ display: "flex", gap: 8, marginBottom: 12 }}>
            <div style={{ ...card, flex: 1, marginBottom: 0, textAlign: "center" }}>
              <div style={label}>Participants</div>
              <div style={value}>{data.participant_count}</div>
            </div>
            <div style={{ ...card, flex: 1, marginBottom: 0, textAlign: "center" }}>
              <div style={label}>Duration</div>
              <div style={value}>{Math.round(data.duration_seconds)}s</div>
            </div>
          </div>

          {/* Per-speaker cards */}
          {(data.analytics || []).map((speaker, idx) => {
            const color = getSpeakerColor(idx);
            return (
              <div key={speaker.speaker} style={{ ...card, borderLeft: `3px solid ${color}` }}>
                {/* Name + speaking % */}
                <div style={{ display: "flex", justifyContent: "space-between", alignItems: "center", marginBottom: 8 }}>
                  <span style={{ fontWeight: 700, color, fontSize: 14 }}>{speaker.speaker}</span>
                  <span style={{ background: `${color}22`, color, borderRadius: 20, padding: "2px 10px", fontSize: 11, fontWeight: 700 }}>
                    {speaker.speaking_percentage}%
                  </span>
                </div>

                {/* Progress bar */}
                <div style={{ marginBottom: 10 }}>
                  <Bar pct={speaker.speaking_percentage} color={color} />
                </div>

                {/* Stats row */}
                <div style={{ display: "flex", gap: 16, marginBottom: 8 }}>
                  <div>
                    <div style={label}>Speaking Time</div>
                    <div style={{ ...value, fontSize: 13 }}>{speaker.speaking_time_seconds}s</div>
                  </div>
                  <div>
                    <div style={label}>Words</div>
                    <div style={{ ...value, fontSize: 13 }}>{speaker.word_count}</div>
                  </div>
                  <div>
                    <div style={label}>WPM</div>
                    <div style={{ ...value, fontSize: 13 }}>{speaker.words_per_minute}</div>
                  </div>
                  <div>
                    <div style={label}>Segments</div>
                    <div style={{ ...value, fontSize: 13 }}>{speaker.segment_count}</div>
                  </div>
                </div>

                {/* Keywords */}
                {speaker.top_keywords && speaker.top_keywords.length > 0 && (
                  <div>
                    <div style={{ ...label, marginBottom: 5 }}>Top Keywords</div>
                    <div style={{ display: "flex", flexWrap: "wrap", gap: 5 }}>
                      {speaker.top_keywords.map((kw) => (
                        <span
                          key={kw}
                          style={{
                            background: `${color}18`,
                            color,
                            border: `1px solid ${color}44`,
                            borderRadius: 20,
                            padding: "2px 9px",
                            fontSize: 11,
                          }}
                        >
                          {kw}
                        </span>
                      ))}
                    </div>
                  </div>
                )}
              </div>
            );
          })}
        </>
      )}
    </div>
  );
}
