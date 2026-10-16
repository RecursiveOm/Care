from app.agents.clinical_nlp import deterministic_extract
from app.agents.monitoring import summarize_timeline, significant_change
from app.agents.safety import safety_gate
from app.agents.vitals import calculate_demo_index


def test_note_extractor_only_returns_known_literal_phrases():
    out = deterministic_extract("Patient reports cough and fever, denies chest pain.")
    assert any(x["phrase"].lower() == "cough" and not x["negated"] for x in out["mentions"])
    assert any(x["phrase"].lower() == "denies chest pain" and x["negated"] for x in out["mentions"])
    assert not any(x["phrase"].lower() == "chest pain" and not x["negated"] for x in out["mentions"])


def test_empty_timeline_abstains():
    summary = summarize_timeline([])
    gate = safety_gate(summary, None)
    assert gate["status"] == "ABSTAIN"


def test_summary_builds_personal_baseline():
    obs = [
        {"id":"a", "type":"heart_rate", "value":70, "unit":"bpm", "observed_at":"2026-01-01T00:00:00+00:00"},
        {"id":"b", "type":"heart_rate", "value":75, "unit":"bpm", "observed_at":"2026-01-02T00:00:00+00:00"},
        {"id":"c", "type":"heart_rate", "value":105, "unit":"bpm", "observed_at":"2026-01-03T00:00:00+00:00"},
        {"id":"d", "type":"spo2", "value":98, "unit":"%", "observed_at":"2026-01-03T00:00:00+00:00"},
        {"id":"e", "type":"respiratory_rate", "value":16, "unit":"breaths/min", "observed_at":"2026-01-03T00:00:00+00:00"},
    ]
    summary = summarize_timeline(obs)
    assert summary["baselines"]["heart_rate"]["center"] == 72.5
    changed, reasons = significant_change(summary)
    assert changed is True
    idx, evidence = calculate_demo_index(summary)
    assert idx > 0
    assert evidence


def test_low_observation_count_abstains():
    summary = summarize_timeline([{"id":"a", "type":"spo2", "value":98, "unit":"%", "observed_at":"2026-01-01T00:00:00+00:00"}])
    assert safety_gate(summary, 0)["status"] == "ABSTAIN"


def test_ollama_failure_falls_back_without_raising(monkeypatch):
    import urllib.request
    from app.agents.clinical_nlp import extract_note
    monkeypatch.setenv("CARE_AI_SLM_MODE", "ollama")
    monkeypatch.setenv("CARE_AI_OLLAMA_BASE_URL", "http://127.0.0.1:1")
    def fail(*args, **kwargs):
        raise OSError("offline")
    monkeypatch.setattr(urllib.request, "urlopen", fail)
    out = extract_note("Synthetic patient reports cough.")
    assert out["mode"] == "fallback"
    assert any(x["phrase"] == "cough" for x in out["mentions"])


def test_unsupported_model_phrase_is_not_added_by_fallback():
    from app.agents.clinical_nlp import deterministic_extract
    out = deterministic_extract("Synthetic patient is resting comfortably.")
    assert out["mentions"] == []
