from __future__ import annotations
import json, os, urllib.request
from typing import Any


def narrative(summary: dict[str, Any], score: int | None, status: str, evidence: list[dict[str, Any]]) -> tuple[str, dict[str, Any]]:
    # Default template is deterministic and cannot invent new facts.
    if score is None:
        template = "Analysis withheld because the safety gate found insufficient evidence. Review the missing-data reasons before retrying."
    elif evidence:
        names = sorted({str(e.get("type")) for e in evidence if e.get("type")})
        template = f"The demo workflow found {len(evidence)} evidence item(s) across {', '.join(names) if names else 'note mentions'}. Status: {status}. This is a software demonstration, not a clinical conclusion."
    else:
        template = f"No selected demo rule fired on the available measurements. Status: {status}. The result does not establish that a patient is healthy."
    if os.getenv("CARE_AI_LLM_ENABLED", "false").lower() != "true":
        return template, {"mode": "disabled", "model": None}
    base = os.getenv("CARE_AI_LLM_BASE_URL", "https://api.openai.com/v1").rstrip("/")
    key = os.getenv("CARE_AI_LLM_API_KEY", "").strip()
    model = os.getenv("CARE_AI_LLM_MODEL", "").strip()
    if not key or not model:
        return template, {"mode": "fallback", "model": model or None, "reason": "missing_configuration"}
    # Only send counts, types, score and status. Never send IDs, raw notes, or note phrases.
    payload_context = {"observation_type_count": summary["types_count"], "observation_count": summary["observations_count"], "signal_index": score, "status": status, "evidence_types": sorted({str(e.get("type")) for e in evidence if e.get("type")}), "evidence_count": len(evidence)}
    request_data = {"model": model, "temperature": 0, "messages": [
        {"role": "system", "content": "Rewrite the supplied engineering-demo metadata in one short neutral sentence. Do not diagnose, recommend treatment, claim probability or add facts. State that the value is demo-only."},
        {"role": "user", "content": json.dumps(payload_context)}
    ]}
    try:
        req = urllib.request.Request(base + "/chat/completions", data=json.dumps(request_data).encode(), headers={"Content-Type": "application/json", "Authorization": "Bearer " + key}, method="POST")
        with urllib.request.urlopen(req, timeout=float(os.getenv("CARE_AI_LLM_TIMEOUT_SECONDS", "12"))) as resp:
            raw = json.loads(resp.read().decode())
        content = raw["choices"][0]["message"]["content"].strip()
        if not content or len(content) > 700:
            raise ValueError("invalid_length")
        # Score and status remain owned by deterministic services.
        return content, {"mode": "used", "model": model, "scope": "deidentified_metadata_only"}
    except Exception as exc:
        return template, {"mode": "fallback", "model": model, "reason": type(exc).__name__}
