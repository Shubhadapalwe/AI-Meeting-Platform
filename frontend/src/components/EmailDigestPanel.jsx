import { useState } from "react";

const API_BASE = "";

export default function EmailDigestPanel({ meetingId, pdfFilename }) {
  const [emails, setEmails] = useState("");
  const [status, setStatus] = useState(null);
  const [result, setResult] = useState(null);

  async function handleSend() {
    const list = emails
      .split(/[\s,;]+/)
      .map((e) => e.trim())
      .filter((e) => e.includes("@"));

    if (!list.length) {
      setStatus("error");
      setResult({ message: "Enter at least one valid email address." });
      return;
    }

    setStatus("sending");
    setResult(null);

    try {
      const res = await fetch(`${API_BASE}/api/email/send/${meetingId}`, {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ emails: list, pdf_filename: pdfFilename || null }),
      });

      const data = await res.json();
      if (!res.ok) throw new Error(data.detail || "Failed to send digest");

      setResult(data);
      setStatus("done");
    } catch (err) {
      setResult({ message: err.message });
      setStatus("error");
    }
  }

  const isDryRun = result?.status === "dry_run";

  // Parse SMTP error into user-friendly message
  function friendlyError(msg = "") {
    if (msg.includes("535") || msg.includes("BadCredentials") || msg.includes("Username and Password")) {
      return {
        title: "Gmail credentials rejected",
        body: "You must use a Gmail App Password — not your regular Gmail password.",
        steps: [
          "Go to myaccount.google.com/security",
          "Enable 2-Step Verification (if not already on)",
          "Go to myaccount.google.com/apppasswords",
          "Create an App Password named 'Meeting AI'",
          "Copy the 16-character password into .env as SMTP_PASSWORD",
          "Restart with: bash start.sh",
        ],
      };
    }
    if (msg.includes("534") || msg.includes("Application-specific")) {
      return { title: "App Password required", body: msg, steps: [] };
    }
    if (msg.includes("Connection refused") || msg.includes("SMTP")) {
      return { title: "SMTP connection failed", body: "Check SMTP_HOST and SMTP_PORT in your .env file.", steps: [] };
    }
    return { title: "Email error", body: msg, steps: [] };
  }

  const errInfo = status === "error" && result ? friendlyError(result.message) : null;

  return (
    <div style={{ color: "#e5e7eb", fontSize: 13 }}>
      <div style={{ fontWeight: 700, fontSize: 15, marginBottom: 14 }}>
        📧 Send Meeting Digest
      </div>

      <div style={{ marginBottom: 10 }}>
        <div style={{ color: "#9ca3af", fontSize: 11, marginBottom: 5 }}>
          Recipient emails (comma or space separated)
        </div>
        <textarea
          value={emails}
          onChange={(e) => setEmails(e.target.value)}
          placeholder="alice@example.com, bob@example.com"
          rows={3}
          style={{
            width: "100%", background: "rgba(255,255,255,0.05)",
            border: "1px solid rgba(255,255,255,0.12)", borderRadius: 10,
            color: "#e5e7eb", padding: "10px 12px", fontSize: 13,
            resize: "vertical", boxSizing: "border-box",
          }}
        />
      </div>

      {pdfFilename && (
        <div style={{ color: "#34d399", fontSize: 11, marginBottom: 10 }}>
          📄 PDF will be attached: {pdfFilename}
        </div>
      )}
      {!pdfFilename && (
        <div style={{ color: "#6b7280", fontSize: 11, marginBottom: 10 }}>
          💡 Generate PDF in the ✨ Summary tab first to attach it to the email.
        </div>
      )}

      <button
        onClick={handleSend}
        disabled={status === "sending"}
        style={{
          width: "100%",
          background: status === "sending" ? "rgba(37,99,235,0.4)" : "#2563eb",
          color: "#fff", border: "none", borderRadius: 10, padding: "10px",
          fontWeight: 700, fontSize: 13,
          cursor: status === "sending" ? "not-allowed" : "pointer",
          marginBottom: 12,
        }}
      >
        {status === "sending" ? "Sending…" : "Send Digest Email"}
      </button>

      {/* Result */}
      {result && (
        <>
          {isDryRun && (
            <div style={{
              background: "rgba(245,158,11,0.08)", border: "1px solid rgba(245,158,11,0.2)",
              borderRadius: 12, padding: "12px 14px", color: "#fde68a",
            }}>
              <div style={{ fontWeight: 700, marginBottom: 4 }}>⚠ Dry Run — SMTP not configured</div>
              <div style={{ fontSize: 12 }}>
                Email content saved to server log. To send real emails:
                copy <code>.env.example</code> → <code>.env</code> and fill in Gmail credentials.
              </div>
              {result.log_path && (
                <div style={{ fontSize: 11, marginTop: 6, color: "#9ca3af" }}>Log: {result.log_path}</div>
              )}
            </div>
          )}

          {status === "error" && errInfo && (
            <div style={{
              background: "rgba(239,68,68,0.08)", border: "1px solid rgba(239,68,68,0.25)",
              borderRadius: 12, padding: "12px 14px",
            }}>
              <div style={{ color: "#fca5a5", fontWeight: 700, marginBottom: 6 }}>
                ❌ {errInfo.title}
              </div>
              <div style={{ color: "#fca5a5", fontSize: 12, marginBottom: errInfo.steps.length ? 8 : 0 }}>
                {errInfo.body}
              </div>
              {errInfo.steps.length > 0 && (
                <ol style={{ color: "#fcd34d", fontSize: 11, margin: 0, paddingLeft: 18, lineHeight: 1.8 }}>
                  {errInfo.steps.map((s, i) => <li key={i}>{s}</li>)}
                </ol>
              )}
            </div>
          )}

          {status === "done" && !isDryRun && (
            <div style={{
              background: "rgba(16,185,129,0.08)", border: "1px solid rgba(16,185,129,0.2)",
              borderRadius: 12, padding: "12px 14px", color: "#6ee7b7",
            }}>
              <div style={{ fontWeight: 700, marginBottom: 4 }}>✅ {result.message}</div>
              {result.sent?.length > 0 && (
                <div style={{ fontSize: 12 }}>Sent to: {result.sent.join(", ")}</div>
              )}
              {result.failed?.length > 0 && (
                <div style={{ fontSize: 12, marginTop: 4, color: "#fca5a5" }}>
                  Failed: {result.failed.map((f) => f.email).join(", ")}
                </div>
              )}
            </div>
          )}
        </>
      )}
    </div>
  );
}
