from __future__ import annotations
from typing import Any


def safety_gate(summary: dict[str, Any], signal_index: int | None) -> dict[str, Any]:
    reasons = []
    if summary["observations_count"] < 3:
        reasons.append("Fewer than three observations are available; evidence is insufficient for this demo workflow.")
    if summary["types_count"] < 2:
        reasons.append("Fewer than two distinct observation types are available.")
    if signal_index is None:
        reasons.append("A score could not be calculated.")
    if reasons:
        return {"status": "ABSTAIN", "reasons": reasons, "safe_to_display_index": False}
    status = "REVIEW" if signal_index >= 25 else "MONITOR"
    return {"status": status, "reasons": ["Software-demo safety checks passed; clinician review is still required for any real-world interpretation."], "safe_to_display_index": True}
