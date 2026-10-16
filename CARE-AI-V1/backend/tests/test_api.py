import os
from pathlib import Path
from fastapi.testclient import TestClient

# Must set the DB path before importing the application.
def test_full_demo_flow(tmp_path, monkeypatch):
    monkeypatch.setenv("CARE_AI_DB_PATH", str(tmp_path / "test.db"))
    monkeypatch.setenv("CARE_AI_SLM_MODE", "rules")
    monkeypatch.setenv("CARE_AI_LLM_ENABLED", "false")
    from app.main import app
    with TestClient(app) as client:
        home = client.get("/")
        assert home.status_code == 200 and "CARE-AI" in home.text
        asset = client.get("/assets/app.js")
        assert asset.status_code == 200 and "Run analysis" in asset.text
        health = client.get("/api/health")
        assert health.status_code == 200 and health.json()["status"] == "ok"
        seed = client.post("/api/demo/seed")
        assert seed.status_code == 200
        patient_id = seed.json()["patient_id"]
        timeline = client.get(f"/api/patients/{patient_id}/timeline")
        assert timeline.status_code == 200
        assert len(timeline.json()["observations"]) >= 10
        note = client.post(f"/api/patients/{patient_id}/notes", json={"note_text":"Synthetic demo note: cough reported; denies fever."})
        assert note.status_code == 201
        result = client.post(f"/api/patients/{patient_id}/analyze")
        assert result.status_code == 200
        body = result.json()
        assert body["status"] in {"MONITOR", "REVIEW", "ABSTAIN"}
        assert "safety" in body and "evidence" in body and "metadata" in body
        review = client.post(f"/api/analyses/{body['id']}/review", json={"outcome":"accepted_for_review", "reviewer_label":"test-reviewer"})
        assert review.status_code == 201
        audit = client.get(f"/api/patients/{patient_id}/audit")
        assert audit.status_code == 200
        assert any(e["action"] == "analysis.reviewed" for e in audit.json()["events"])


def test_observation_validation(tmp_path, monkeypatch):
    monkeypatch.setenv("CARE_AI_DB_PATH", str(tmp_path / "test_validation.db"))
    from app.main import app
    with TestClient(app) as client:
        pid = client.post("/api/patients", json={"display_name":"Synthetic test"}).json()["id"]
        bad = client.post(f"/api/patients/{pid}/observations", json={"type":"spo2", "value":98, "unit":"bpm"})
        assert bad.status_code == 422
