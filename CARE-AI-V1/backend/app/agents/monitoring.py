from __future__ import annotations
from statistics import median
from typing import Any


def summarize_timeline(observations: list[dict[str, Any]]) -> dict[str, Any]:
    by_type: dict[str, list[dict[str, Any]]] = {}
    for ob in sorted(observations, key=lambda x: x["observed_at"]):
        by_type.setdefault(ob["type"], []).append(ob)
    latest = {}
    baselines = {}
    deviations = []
    for typ, items in by_type.items():
        latest_item = items[-1]
        baseline_items = items[:-1] if len(items) > 1 else items
        vals = [float(x["value"]) for x in baseline_items]
        center = float(median(vals)) if vals else None
        latest[typ] = latest_item
        baselines[typ] = {"center": center, "n": len(vals), "unit": latest_item["unit"]}
        if center is not None and len(items) > 1:
            delta = float(latest_item["value"]) - center
            if abs(delta) > 0:
                deviations.append({"type": typ, "latest": float(latest_item["value"]), "baseline": center, "delta": delta, "unit": latest_item["unit"], "observation_id": latest_item["id"]})
    return {"latest": latest, "baselines": baselines, "deviations": deviations, "types_count": len(latest), "observations_count": len(observations)}


def significant_change(summary: dict[str, Any]) -> tuple[bool, list[str]]:
    reasons = []
    for item in summary["deviations"]:
        typ, d = item["type"], item["delta"]
        demo_deltas = {"heart_rate": 20, "spo2": 3, "respiratory_rate": 5, "temperature": 0.8, "systolic_bp": 20, "diastolic_bp": 12}
        if typ in demo_deltas and abs(d) >= demo_deltas[typ]:
            reasons.append(f"{typ} moved {d:+g} {item['unit']} from the recent personal baseline (demo rule).")
    return bool(reasons), reasons
