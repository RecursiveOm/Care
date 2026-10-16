from __future__ import annotations
import json, os, re, urllib.request, urllib.error
from typing import Any

# Phrase matching examples for software tests, not diagnostic terms.
BASE_TERMS = [
    "shortness of breath", "breathlessness", "cough", "chest pain", "sore throat",
    "dizziness", "fatigue", "nausea", "vomiting", "headache", "fever", "chills",
    "confusion", "worsening pain"
]
NEGATION_WORDS = r"(?:no|denies|denied|without|not experiencing)"
SCHEMA = {
    "type": "object",
    "properties": {
        "mentions": {"type": "array", "items": {"type": "object", "properties": {
            "phrase": {"type": "string"}, "negated": {"type": "boolean"}
        }, "required": ["phrase", "negated"]}},
        "brief_summary": {"type": "string"}
    },
    "required": ["mentions", "brief_summary"]
}


def deterministic_extract(note_text: str) -> dict[str, Any]:
    mentions = []
    occupied = []
    # First identify explicitly negated phrases (e.g. "denies fever").
    for term in BASE_TERMS:
        pattern = re.compile(rf"\b{NEGATION_WORDS}\s+(?:any\s+)?{re.escape(term)}\b", re.IGNORECASE)
        for match in pattern.finditer(note_text):
            phrase = match.group(0)
            mentions.append({"phrase": phrase, "negated": True})
            occupied.append(match.span())
    # Then collect unnegated exact mentions, excluding terms already covered by a negation phrase.
    for term in BASE_TERMS:
        pattern = re.compile(rf"\b{re.escape(term)}\b", re.IGNORECASE)
        for match in pattern.finditer(note_text):
            if any(a <= match.start() and match.end() <= b for a, b in occupied):
                continue
            mentions.append({"phrase": match.group(0), "negated": False})
            occupied.append(match.span())
    mentions.sort(key=lambda x: note_text.lower().find(x["phrase"].lower()))
    return {"mentions": mentions, "brief_summary": "Extracted literal phrase mentions only; this is not a clinical interpretation."}


def extract_note(note_text: str) -> dict[str, Any]:
    mode = os.getenv("CARE_AI_SLM_MODE", "rules").strip().lower()
    if mode != "ollama":
        return {**deterministic_extract(note_text), "mode": "rules", "model": None}

    base = os.getenv("CARE_AI_OLLAMA_BASE_URL", "http://localhost:11434").rstrip("/")
    model = os.getenv("CARE_AI_SLM_MODEL", "qwen3.5:0.8b")
    try:
        import urllib.request
        payload = {
            "model": model,
            "messages": [
                {"role": "system", "content": "You extract literal symptom/sign phrase mentions from text only. Do not diagnose, assess risk, recommend treatment, or infer an unstated fact. Preserve short exact source phrases. Return the required JSON schema."},
                {"role": "user", "content": "Extract only explicitly present clinical phrase mentions from this note. Do not add terms not found in the input. Note:\n" + note_text}
            ],
            "stream": False,
            "format": SCHEMA,
            "options": {"temperature": 0}
        }
        timeout = float(os.getenv("CARE_AI_SLM_TIMEOUT_SECONDS", "18"))
        req = urllib.request.Request(base + "/api/chat", data=json.dumps(payload).encode(), headers={"Content-Type": "application/json"}, method="POST")
        with urllib.request.urlopen(req, timeout=timeout) as resp:
            raw = json.loads(resp.read().decode())
        content = raw.get("message", {}).get("content", "")
        parsed = json.loads(content)
        source_low = note_text.lower()
        grounded = []
        for item in parsed.get("mentions", []):
            phrase = str(item.get("phrase", "")).strip()
            if phrase and phrase.lower() in source_low:
                grounded.append({"phrase": phrase, "negated": bool(item.get("negated", False))})
        return {"mentions": grounded, "brief_summary": "Literal mentions extracted by local SLM; terms not present in the source were discarded.", "mode": "ollama", "model": model}
    except Exception as exc:
        # Do not leak note text or arbitrary model output to logs / API errors.
        fallback = deterministic_extract(note_text)
        return {**fallback, "mode": "fallback", "model": model, "fallback_reason": type(exc).__name__}
