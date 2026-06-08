from pathlib import Path
import json
import re

BACKEND_ROOT = Path(__file__).resolve().parent.parent.parent
STORAGE_DIR = BACKEND_ROOT / "storage"

TRANSCRIPTS_DIR = STORAGE_DIR / "transcripts"
SUMMARIES_DIR = STORAGE_DIR / "summaries"
SPEAKERS_DIR = STORAGE_DIR / "speakers"


def load_latest_json(folder: Path, meeting_id: str):
    if not folder.exists():
        return None
    matched_items = []
    for file in folder.glob("*.json"):
        try:
            with open(file, "r", encoding="utf-8") as f:
                data = json.load(f)
            if data.get("meeting_id") == meeting_id:
                matched_items.append(data)
        except Exception:
            continue  # skip corrupted/empty files
    if not matched_items:
        return None
    matched_items.sort(key=lambda x: x.get("created_at", ""), reverse=True)
    return matched_items[0]


def build_speaker_context(speakers):
    if not speakers:
        return "No speaker analysis available."
    analytics = speakers.get("analytics", [])
    if not analytics:
        return "No speaker analytics available."
    lines = []
    for item in analytics:
        lines.append(
            f"{item.get('speaker')}: "
            f"{item.get('speaking_time_seconds')} seconds, "
            f"{item.get('speaking_percentage')}%, "
            f"{item.get('word_count')} words"
        )
    return "\n".join(lines)


def _keyword_answer(question: str, transcript_text: str, summary: dict) -> str:
    """Extractive fallback when Ollama is unavailable."""
    stop_words = {"what","who","when","where","how","why","is","are","was",
                  "were","the","a","an","in","of","and","or","did","does","this","that"}
    q_words = set(re.sub(r"[^\w\s]", "", question.lower()).split()) - stop_words

    sentences = re.split(r"(?<=[.!?])\s+", transcript_text)
    scored = []
    for s in sentences:
        score = sum(1 for w in q_words if w in s.lower())
        if score > 0:
            scored.append((score, s.strip()))
    scored.sort(reverse=True)
    top = [s for _, s in scored[:3]]

    if top:
        return " ".join(top)

    if summary:
        q_lower = question.lower()
        if any(w in q_lower for w in ["action", "task", "todo", "follow"]):
            items = summary.get("action_items", [])
            if items:
                return "Action items: " + "; ".join(items)
        if any(w in q_lower for w in ["decision", "decided", "agreed"]):
            items = summary.get("decisions", [])
            if items:
                return "Decisions: " + "; ".join(items)
        short = summary.get("short_summary", "")
        if short:
            return short

    return "This topic was not clearly discussed in the meeting transcript."


def answer_question(meeting_id: str, question: str):
    transcript = load_latest_json(TRANSCRIPTS_DIR, meeting_id)
    summary = load_latest_json(SUMMARIES_DIR, meeting_id)
    speakers = load_latest_json(SPEAKERS_DIR, meeting_id)

    if not transcript:
        raise FileNotFoundError("No transcript found. Please generate transcript first.")

    transcript_text = transcript.get("full_text", "").strip()
    if not transcript_text:
        raise ValueError("Transcript is empty.")

    try:
        from app.services.llm_service import ask_llama
        summary_text = json.dumps(summary, indent=2, ensure_ascii=False) if summary else "No summary."
        speaker_context = build_speaker_context(speakers)
        prompt = (
            "You are an AI meeting assistant.\n"
            "Answer the question using ONLY the meeting transcript below.\n"
            "If the answer is not in the transcript, say so.\n\n"
            f"Transcript:\n{transcript_text}\n\n"
            f"Summary:\n{summary_text}\n\n"
            f"Speakers:\n{speaker_context}\n\n"
            f"Question: {question}\n\nAnswer:"
        )
        answer = ask_llama(prompt)
        return {"answer": answer, "source": "llama3.2_local_llm"}
    except Exception:
        answer = _keyword_answer(question, transcript_text, summary)
        return {"answer": answer, "source": "keyword_search_fallback"}
