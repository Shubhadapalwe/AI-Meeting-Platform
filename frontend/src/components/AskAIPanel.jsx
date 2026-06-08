import { useState } from "react";
import { askAI } from "../services/api";

export default function AskAIPanel({ meetingId }) {
  const [question, setQuestion] = useState("");
  const [loading, setLoading] = useState(false);
  const [answer, setAnswer] = useState(null);
  const [error, setError] = useState("");

  const SUGGESTED = [
    "What were the main topics discussed?",
    "Who spoke the most?",
    "What are the action items?",
    "Were any decisions made?",
  ];

  async function handleAsk(q) {
    const query = (q || question).trim();
    if (!query) return;
    try {
      setLoading(true);
      setError("");
      setAnswer(null);
      const data = await askAI(meetingId, query);
      setAnswer(data);
    } catch (err) {
      setError(err.message || "Ask AI failed. Generate a transcript first.");
    } finally {
      setLoading(false);
    }
  }

  return (
    <div style={{ padding: "0 16px" }}>
      <div style={{ display: "flex", gap: 8, marginBottom: 8 }}>
        <input
          value={question}
          onChange={(e) => setQuestion(e.target.value)}
          onKeyDown={(e) => e.key === "Enter" && handleAsk()}
          placeholder="Ask about this meeting..."
          style={{
            flex: 1, background: "rgba(255,255,255,0.07)", border: "1px solid rgba(255,255,255,0.12)",
            borderRadius: 10, padding: "10px 12px", color: "#e2e8f0", fontSize: 13, outline: "none",
          }}
        />
        <button
          onClick={() => handleAsk()}
          disabled={loading || !question.trim()}
          style={{
            background: "#2563eb", color: "white", border: "none", borderRadius: 10,
            padding: "10px 16px", fontWeight: 800, cursor: "pointer", fontSize: 13,
            opacity: (loading || !question.trim()) ? 0.5 : 1,
          }}
        >
          {loading ? "..." : "Ask"}
        </button>
      </div>

      <div style={{ display: "flex", gap: 6, flexWrap: "wrap", marginBottom: 10 }}>
        {SUGGESTED.map((s) => (
          <button
            key={s}
            onClick={() => { setQuestion(s); handleAsk(s); }}
            disabled={loading}
            style={{
              background: "rgba(255,255,255,0.06)", color: "#94a3b8",
              border: "1px solid rgba(255,255,255,0.1)", borderRadius: 99,
              padding: "4px 10px", fontSize: 11, cursor: "pointer", fontWeight: 600,
            }}
          >
            {s}
          </button>
        ))}
      </div>

      {error && <p style={{ color: "#f87171", fontSize: 12 }}>{error}</p>}

      {answer && (
        <div style={{
          background: "rgba(255,255,255,0.04)", border: "1px solid rgba(255,255,255,0.1)",
          borderRadius: 12, padding: "12px 14px",
        }}>
          <p style={{ color: "#93c5fd", fontSize: 12, margin: "0 0 6px", fontWeight: 700 }}>
            Q: {answer.question}
          </p>
          <p style={{ color: "#e2e8f0", fontSize: 13, margin: 0, lineHeight: 1.6 }}>
            {answer.answer}
          </p>
          <p style={{ color: "#4b5563", fontSize: 11, margin: "8px 0 0" }}>
            via {answer.generated_by}
          </p>
        </div>
      )}
    </div>
  );
}
