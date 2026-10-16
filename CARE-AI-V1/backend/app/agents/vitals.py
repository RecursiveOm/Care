from __future__ import annotations
from typing import Any

# Illustrative software rules only; not clinical thresholds or a medical guideline.
DEMO_RULES = [
    ("spo2", lambda v: v < 93, 24, "Latest SpO2 crosses an illustrative demo threshold."),
    ("spo2", lambda v: v < 95, 10, "Latest SpO2 is below an illustrative demo threshold."),
    ("heart_rate", lambda v: v >= 120, 18, "Latest heart rate crosses an illustrative demo threshold."),
    ("heart_rate", lambda v: v >= 110, 8, "Latest heart rate is above an illustrative demo threshold."),
    ("respiratory_rate", lambda v: v >= 24, 18, "Latest respiratory rate crosses an illustrative demo threshold."),
    ("temperature", lambda v: v >= 38.0, 10, "Latest temperature crosses an illustrative demo threshold."),
    ("systolic_bp", lambda v: v <= 90, 18, "Latest systolic blood pressure crosses an illustrative demo threshold."),
]


def calculate_demo_index(summary: dict[str, Any]) -> tuple[int, list[dict[str, Any]]]:
    points = 0
    evidence = []
    latest = summary["latest"]
    for typ, condition, weight, message in DEMO_RULES:
        item = latest.get(typ)
        if item and condition(float(item["value"])):
            points += weight
            evidence.append({"kind": "illustrative_threshold", "type": typ, "observation_id": item["id"], "value": item["value"], "unit": item["unit"], "message": message})
    for d in summary["deviations"]:
        typ, delta = d["type"], d["delta"]
        # Count only predefined worsening-oriented deviations; generic changes aren't a diagnosis.
        worsening = ((typ == "spo2" and delta <= -3) or
                     (typ == "heart_rate" and delta >= 20) or
                     (typ == "respiratory_rate" and delta >= 5) or
                     (typ == "temperature" and delta >= 0.8) or
                     (typ == "systolic_bp" and delta <= -20))
        if worsening:
            points += 10
            evidence.append({"kind": "baseline_deviation", "type": typ, "observation_id": d["observation_id"], "value": d["latest"], "baseline": d["baseline"], "delta": delta, "unit": d["unit"], "message": f"{typ} differs from personal baseline by {delta:+g} {d['unit']} (demo rule)."})
    return min(100, points), evidence
