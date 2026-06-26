import { useState } from "react";
import { generateAISummary, generateMeetingPDF, getPDFDownloadUrl } from "../services/api";

export default function AISummaryPanel({ meetingId, onPdfGenerated }) {
  const [loading, setLoading] = useState(false);
  const [pdfLoading, setPdfLoading] = useState(false);
  const [summary, setSummary] = useState(null);
  const [pdfFilename, setPdfFilename] = useState(null);
  const [error, setError] = useState("");

  async function handleGenerate() {
    try {
      setLoading(true);
      setError("");
      const data = await generateAISummary(meetingId);
      setSummary(data);
    } catch (err) {
      const msg = err.message || "";
      setError(
        msg.includes("No transcript") || msg.includes("404")
          ? "No transcript found. Generate transcript first."
          : msg || "Summary generation failed. Generate a transcript first."
      );
    } finally {
      setLoading(false);
    }
  }

  async function handleGeneratePDF() {
    try {
      setPdfLoading(true);
      setError("");
      const result = await generateMeetingPDF(meetingId);
      const filename = result.pdf_filename;
      setPdfFilename(filename);
      if (onPdfGenerated) onPdfGenerated(filename);   // ← notify parent
      window.open(getPDFDownloadUrl(result.download_url), "_blank");
    } catch (err) {
      const msg = err.message || "";
      setError(
        msg.includes("No transcript") || msg.includes("404")
          ? "PDF failed. Generate transcript and summary first."
          : msg || "PDF generation failed."
      );
    } finally {
      setPdfLoading(false);
    }
  }

  return (
    <div style={{ padding: "0 16px" }}>
      {/* Step guide */}
      <div style={{ fontSize: 11, color: "#64748b", marginBottom: 10, lineHeight: 1.6 }}>
        Step 1: Generate Transcript (📝 tab) → Step 2: Generate Summary → Step 3: Generate PDF → Step 4: Send Email (📧 tab)
      </div>

      <button
        onClick={handleGenerate}
        disabled={loading}
        style={{
          width: "100%", background: loading ? "#1d4ed8" : "#2563eb",
          color: "white", border: "none", borderRadius: 12,
          padding: "12px 0", fontWeight: 800,
          cursor: loading ? "not-allowed" : "pointer", fontSize: 14,
        }}
      >
        {loading ? "Generating summary..." : "✨ Generate AI Summary"}
      </button>

      <button
        onClick={handleGeneratePDF}
        disabled={pdfLoading}
        style={{
          width: "100%", background: pdfLoading ? "#15803d" : "#16a34a",
          color: "white", border: "none", borderRadius: 12,
          padding: "12px 0", fontWeight: 800,
          cursor: pdfLoading ? "not-allowed" : "pointer",
          fontSize: 14, marginTop: 10,
        }}
      >
        {pdfLoading ? "Generating PDF..." : "📄 Generate Meeting Minutes PDF"}
      </button>

      {pdfFilename && (
        <div style={{ fontSize: 11, color: "#34d399", marginTop: 6, textAlign: "center" }}>
          ✅ PDF ready: {pdfFilename} — switch to 📧 tab to send it
        </div>
      )}

      {error && (
        <p style={{ color: "#f87171", fontSize: 12, marginTop: 8 }}>{error}</p>
      )}

      {summary && (
        <div style={{ marginTop: 14, color: "#cbd5e1", fontSize: 13 }}>
          <div style={{
            background: "rgba(37,99,235,0.1)",
            border: "1px solid rgba(37,99,235,0.3)",
            borderRadius: 12, padding: "12px 14px", marginBottom: 12,
          }}>
            <strong style={{ color: "#93c5fd", fontSize: 12 }}>
              📊 {summary.word_count} words · via {summary.generated_by}
            </strong>
            <p style={{ margin: "8px 0 0", lineHeight: 1.6 }}>{summary.short_summary}</p>
          </div>

          <strong style={{ color: "#e2e8f0" }}>✅ Action Items</strong>
          <ul style={{ paddingLeft: 18, marginTop: 6 }}>
            {summary.action_items?.map((item, i) => (
              <li key={i} style={{ marginBottom: 4 }}>{item}</li>
            ))}
          </ul>

          <strong style={{ color: "#e2e8f0" }}>🎯 Decisions</strong>
          <ul style={{ paddingLeft: 18, marginTop: 6 }}>
            {summary.decisions?.map((item, i) => (
              <li key={i} style={{ marginBottom: 4 }}>{item}</li>
            ))}
          </ul>
        </div>
      )}
    </div>
  );
}
