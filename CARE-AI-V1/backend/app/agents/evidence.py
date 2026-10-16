from __future__ import annotations
from typing import Any


def build_evidence(summary: dict[str, Any], score_evidence: list[dict[str, Any]], note_extractions: list[dict[str, Any]]) -> list[dict[str, Any]]:
    evidence = list(score_evidence)
    for item in summary["deviations"]:
        evidence.append({"kind": "baseline_comparison", "type": item["type"], "observation_id": item["observation_id"], "value": item["latest"], "baseline": item["baseline"], "delta": item["delta"], "unit": item["unit"], "message": f"Observed value {item['latest']:g} {item['unit']} vs median baseline {item['baseline']:g} {item['unit']}."})
    for note in note_extractions:
        for mention in note.get("mentions", []):
            evidence.append({"kind": "note_mention", "note_id": note.get("note_id"), "phrase": mention["phrase"], "negated": mention.get("negated", False), "message": f"Literal note phrase: {mention['phrase']}"})
    return evidence
