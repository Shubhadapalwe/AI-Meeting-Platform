import { useEffect, useState } from "react";
import { getMeetingHistory, searchTranscripts } from "../services/api";

export default function MeetingHistory({ onJoin, onBack }) {
  const [meetings, setMeetings] = useState([]);
  const [loading, setLoading] = useState(true);
  const [search, setSearch] = useState("");
  const [searchResults, setSearchResults] = useState(null);
  const [searching, setSearching] = useState(false);

  useEffect(() => {
    getMeetingHistory()
      .then((d) => setMeetings(d.meetings || []))
      .catch(() => setMeetings([]))
      .finally(() => setLoading(false));
  }, []);

  async function handleSearch() {
    if (!search.trim()) { setSearchResults(null); return; }
    setSearching(true);
    try {
      const data = await searchTranscripts(search.trim());
      setSearchResults(data);
    } catch {
      setSearchResults({ results: [], total: 0, query: search });
    } finally {
      setSearching(false);
    }
  }

  const card = {
    background: "rgba(255,255,255,0.04)",
    border: "1px solid rgba(255,255,255,0.08)",
    borderRadius: 16, padding: "16px 20px", marginBottom: 12,
  };

  return (
    <main style={{ minHeight: "100vh", background: "#0a0a0f", color: "#e5e7eb", padding: "32px 24px" }}>
      <div style={{ maxWidth: 720, margin: "0 auto" }}>
        <div style={{ display: "flex", alignItems: "center", gap: 12, marginBottom: 24 }}>
          <button
            onClick={onBack}
            style={{
              background: "rgba(255,255,255,0.07)", border: "none", color: "#e5e7eb",
              borderRadius: 10, padding: "8px 14px", cursor: "pointer", fontWeight: 700,
            }}
          >
            ← Back
          </button>
          <h1 style={{ margin: 0, fontSize: 22 }}>📋 Meeting History</h1>
        </div>

        {/* Search */}
        <div style={{ display: "flex", gap: 8, marginBottom: 24 }}>
          <input
            value={search}
            onChange={(e) => setSearch(e.target.value)}
            onKeyDown={(e) => e.key === "Enter" && handleSearch()}
            placeholder="Search across all transcripts..."
            style={{
              flex: 1, background: "rgba(255,255,255,0.07)",
              border: "1px solid rgba(255,255,255,0.12)", borderRadius: 10,
              padding: "10px 14px", color: "#e2e8f0", fontSize: 14, outline: "none",
            }}
          />
          <button
            onClick={handleSearch}
            disabled={searching}
            style={{
              background: "#2563eb", color: "white", border: "none", borderRadius: 10,
              padding: "10px 18px", fontWeight: 800, cursor: "pointer",
            }}
          >
            {searching ? "..." : "Search"}
          </button>
          {searchResults && (
            <button
              onClick={() => { setSearchResults(null); setSearch(""); }}
              style={{
                background: "transparent", color: "#94a3b8",
                border: "1px solid rgba(255,255,255,0.1)", borderRadius: 10,
                padding: "10px 14px", cursor: "pointer",
              }}
            >
              Clear
            </button>
          )}
        </div>

        {/* Search Results */}
        {searchResults && (
          <div style={{ marginBottom: 24 }}>
            <p style={{ color: "#94a3b8", fontSize: 13, marginBottom: 12 }}>
              {searchResults.total} result(s) for "{searchResults.query}"
            </p>
            {searchResults.results.map((r, i) => (
              <div key={i} style={card}>
                <p style={{ margin: "0 0 8px", fontWeight: 700, color: "#38bdf8" }}>
                  Meeting {r.meeting_id} · {r.total_matches} match(es)
                </p>
                {r.matching_segments.map((s, j) => (
                  <div key={j} style={{
                    background: "rgba(56,189,248,0.07)", borderRadius: 8,
                    padding: "6px 10px", marginBottom: 6, fontSize: 13,
                  }}>
                    <span style={{ color: "#4b5563", fontSize: 11 }}>[{s.start}s] </span>
                    {s.speaker && (
                      <span style={{ color: "#a78bfa", fontSize: 11, fontWeight: 700 }}>
                        {s.speaker}:{" "}
                      </span>
                    )}
                    {s.text}
                  </div>
                ))}
              </div>
            ))}
            {searchResults.total === 0 && (
              <p style={{ color: "#64748b" }}>No matches found.</p>
            )}
          </div>
        )}

        {/* Meeting list */}
        {loading ? (
          <p style={{ color: "#64748b" }}>Loading meetings...</p>
        ) : meetings.length === 0 ? (
          <div style={card}>
            <p style={{ color: "#64748b", textAlign: "center" }}>No meetings yet. Create your first meeting!</p>
          </div>
        ) : (
          meetings.map((m) => (
            <div key={m.meeting_id} style={card}>
              <div style={{ display: "flex", justifyContent: "space-between", alignItems: "flex-start" }}>
                <div>
                  <h3 style={{ margin: "0 0 4px", fontSize: 16 }}>{m.title}</h3>
                  <p style={{ margin: 0, color: "#64748b", fontSize: 12 }}>
                    Host: {m.host_name} · ID: {m.meeting_id}
                  </p>
                </div>
                <div style={{ display: "flex", gap: 8 }}>
                  {m.has_transcript && (
                    <span style={{
                      background: "rgba(52,211,153,0.15)", color: "#34d399",
                      padding: "3px 10px", borderRadius: 99, fontSize: 11, fontWeight: 700,
                    }}>
                      ✓ Transcript
                    </span>
                  )}
                  <button
                    onClick={() => onJoin(m)}
                    style={{
                      background: "#2563eb", color: "white", border: "none",
                      borderRadius: 10, padding: "6px 14px", cursor: "pointer",
                      fontWeight: 700, fontSize: 12,
                    }}
                  >
                    Rejoin
                  </button>
                </div>
              </div>
              {m.has_transcript && (
                <div style={{
                  marginTop: 10, display: "flex", gap: 16, fontSize: 12, color: "#94a3b8",
                }}>
                  <span>⏱ {m.transcript_duration}s</span>
                  <span>📝 {m.transcript_words} words</span>
                </div>
              )}
            </div>
          ))
        )}
      </div>
    </main>
  );
}
