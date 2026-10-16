from __future__ import annotations
import json, os, uuid
from datetime import datetime, timezone, timedelta
from contextlib import asynccontextmanager
from pathlib import Path
from typing import Any
from fastapi import FastAPI, HTTPException
from fastapi.responses import FileResponse
from fastapi.staticfiles import StaticFiles
from fastapi.middleware.cors import CORSMiddleware
from dotenv import load_dotenv

load_dotenv(Path(__file__).resolve().parents[1] / ".env")
from .db import connect, init_db, json_load
from .schemas import PatientCreate, ObservationCreate, NoteCreate, ReviewCreate, now_iso, UNITS
from .agents.clinical_nlp import extract_note
from .agents.monitoring import summarize_timeline, significant_change
from .agents.vitals import calculate_demo_index
from .agents.safety import safety_gate
from .agents.evidence import build_evidence
from .services.llm_narration import narrative

@asynccontextmanager
async def lifespan(_app):
    init_db()
    yield


app = FastAPI(title="CARE-AI V1 API", version="1.0.0", description="Cost-first synthetic-data longitudinal monitoring prototype. Not for clinical decision-making.", lifespan=lifespan)
_origins = [x.strip() for x in os.getenv("CARE_AI_CORS_ORIGINS", "http://localhost:5173,http://127.0.0.1:5173").split(",") if x.strip()]
app.add_middleware(CORSMiddleware, allow_origins=_origins, allow_credentials=False, allow_methods=["GET", "POST", "OPTIONS"], allow_headers=["Content-Type"])


def uid(prefix: str) -> str:
    return f"{prefix}_{uuid.uuid4().hex[:12]}"


def audit(patient_id: str, action: str, component: str, status: str = "ok", details: dict[str, Any] | None = None):
    with connect() as con:
        con.execute("INSERT INTO audit_events(id,patient_id,action,component,status,details_json,created_at) VALUES(?,?,?,?,?,?,?)",
                    (uid("evt"), patient_id, action, component, status, json.dumps(details or {}), now_iso()))


def patient_exists(patient_id: str) -> bool:
    with connect() as con:
        return con.execute("SELECT 1 FROM patients WHERE id=?", (patient_id,)).fetchone() is not None


def require_patient(patient_id: str):
    if not patient_exists(patient_id):
        raise HTTPException(status_code=404, detail="Patient not found")


def fetch_observations(patient_id: str) -> list[dict[str, Any]]:
    with connect() as con:
        rows = con.execute("SELECT * FROM observations WHERE patient_id=? ORDER BY observed_at ASC", (patient_id,)).fetchall()
    return [dict(r) for r in rows]


def fetch_notes(patient_id: str) -> list[dict[str, Any]]:
    with connect() as con:
        rows = con.execute("SELECT * FROM clinical_notes WHERE patient_id=? ORDER BY created_at ASC", (patient_id,)).fetchall()
    result = []
    for r in rows:
        obj = dict(r)
        obj["extracted"] = json_load(obj.pop("extracted_json", "{}"), {})
        result.append(obj)
    return result


@app.get("/api/health")
def health():
    return {"status": "ok", "app": "CARE-AI V1", "version": "1.0.0", "slm_mode": os.getenv("CARE_AI_SLM_MODE", "rules"), "llm_enabled": os.getenv("CARE_AI_LLM_ENABLED", "false").lower() == "true", "data_mode": "synthetic_or_deidentified_only"}


@app.get("/api/patients")
def list_patients():
    with connect() as con:
        rows = con.execute("SELECT p.*, (SELECT COUNT(*) FROM observations o WHERE o.patient_id=p.id) AS observation_count FROM patients p ORDER BY p.created_at DESC").fetchall()
    return {"patients": [dict(r) for r in rows]}


@app.post("/api/patients", status_code=201)
def create_patient(payload: PatientCreate):
    patient_id = uid("patient")
    created = now_iso()
    with connect() as con:
        con.execute("INSERT INTO patients(id,display_name,created_at,data_kind) VALUES(?,?,?,?)", (patient_id, payload.display_name, created, payload.data_kind))
    audit(patient_id, "patient.created", "api", details={"data_kind": payload.data_kind})
    return {"id": patient_id, "display_name": payload.display_name, "created_at": created, "data_kind": payload.data_kind}


@app.post("/api/demo/seed")
def seed_demo():
    patient_id = "patient-demo-001"
    now = datetime.now(timezone.utc)
    with connect() as con:
        row = con.execute("SELECT id FROM patients WHERE id=?", (patient_id,)).fetchone()
        if not row:
            con.execute("INSERT INTO patients(id,display_name,created_at,data_kind) VALUES(?,?,?,?)", (patient_id, "Demo Patient (Synthetic)", now_iso(), "synthetic"))
        n = con.execute("SELECT COUNT(*) AS n FROM observations WHERE patient_id=?", (patient_id,)).fetchone()["n"]
        created = 0
        if n == 0:
            examples = [
                ("heart_rate", 76, "bpm", 5), ("spo2", 98, "%", 5), ("respiratory_rate", 16, "breaths/min", 5), ("temperature", 36.8, "C", 5), ("systolic_bp", 120, "mmHg", 5),
                ("heart_rate", 79, "bpm", 3), ("spo2", 97, "%", 3), ("respiratory_rate", 17, "breaths/min", 3), ("temperature", 36.9, "C", 3), ("systolic_bp", 122, "mmHg", 3),
                ("heart_rate", 106, "bpm", 0), ("spo2", 94, "%", 0), ("respiratory_rate", 21, "breaths/min", 0), ("temperature", 37.2, "C", 0), ("systolic_bp", 118, "mmHg", 0),
            ]
            for typ, value, unit, days_ago in examples:
                obs_at = (now - timedelta(days=days_ago, hours=(1 if days_ago else 0))).isoformat()
                con.execute("INSERT INTO observations(id,patient_id,type,value,unit,observed_at,ingested_at,source,quality_flag,source_event_id) VALUES(?,?,?,?,?,?,?,?,?,?)",
                            (uid("obs"), patient_id, typ, value, unit, obs_at, now_iso(), "demo", "valid", f"demo-{typ}-{days_ago}"))
                created += 1
    audit(patient_id, "demo.seeded", "demo", details={"new_observations": created})
    return {"patient_id": patient_id, "created_observations": created, "message": "Synthetic demo patient is ready. Repeated calls do not duplicate observations."}


@app.get("/api/patients/{patient_id}/timeline")
def get_timeline(patient_id: str):
    require_patient(patient_id)
    with connect() as con:
        patient = dict(con.execute("SELECT * FROM patients WHERE id=?", (patient_id,)).fetchone())
    return {"patient": patient, "observations": fetch_observations(patient_id), "notes": fetch_notes(patient_id)}


@app.post("/api/patients/{patient_id}/observations", status_code=201)
def add_observation(patient_id: str, payload: ObservationCreate):
    require_patient(patient_id)
    obs_id = uid("obs")
    observed_at = payload.observed_at.isoformat() if payload.observed_at else now_iso()
    try:
        with connect() as con:
            con.execute("INSERT INTO observations(id,patient_id,type,value,unit,observed_at,ingested_at,source,quality_flag,source_event_id) VALUES(?,?,?,?,?,?,?,?,?,?)",
                        (obs_id, patient_id, payload.type, payload.value, payload.unit, observed_at, now_iso(), payload.source, "valid", payload.source_event_id))
    except Exception as exc:
        if payload.source_event_id:
            with connect() as con:
                existing = con.execute("SELECT * FROM observations WHERE source_event_id=? AND patient_id=?", (payload.source_event_id, patient_id)).fetchone()
            if existing:
                return {"observation": dict(existing), "duplicate": True}
        raise HTTPException(status_code=409, detail="Could not store observation; check for duplicate source_event_id") from exc
    audit(patient_id, "observation.created", "ingestion", details={"observation_id": obs_id, "type": payload.type})
    with connect() as con:
        row = con.execute("SELECT * FROM observations WHERE id=?", (obs_id,)).fetchone()
    return {"observation": dict(row), "duplicate": False}


@app.post("/api/patients/{patient_id}/notes", status_code=201)
def add_note(patient_id: str, payload: NoteCreate):
    require_patient(patient_id)
    note_id = uid("note")
    created = payload.created_at.isoformat() if payload.created_at else now_iso()
    extracted = extract_note(payload.note_text)
    extracted["note_id"] = note_id
    with connect() as con:
        con.execute("INSERT INTO clinical_notes(id,patient_id,note_text,created_at,extraction_mode,extracted_json) VALUES(?,?,?,?,?,?)",
                    (note_id, patient_id, payload.note_text, created, extracted.get("mode", "rules"), json.dumps(extracted)))
    audit(patient_id, "note.created", "clinical_nlp", details={"note_id": note_id, "extraction_mode": extracted.get("mode"), "mention_count": len(extracted.get("mentions", []))})
    return {"note_id": note_id, "created_at": created, "extraction": extracted}


@app.post("/api/patients/{patient_id}/analyze")
def analyze_patient(patient_id: str):
    require_patient(patient_id)
    obs = fetch_observations(patient_id)
    notes = fetch_notes(patient_id)
    summary = summarize_timeline(obs)
    changed, change_reasons = significant_change(summary)
    index, score_evidence = calculate_demo_index(summary)
    if summary["observations_count"] == 0:
        index_or_none = None
        score_evidence = []
    else:
        index_or_none = index
    note_extracts = []
    for note in notes:
        ext = note.get("extracted") or {}
        if not ext:
            ext = extract_note(note["note_text"])
        ext["note_id"] = note["id"]
        note_extracts.append(ext)
    evidence = build_evidence(summary, score_evidence, note_extracts)
    safety = safety_gate(summary, index_or_none)
    status = safety["status"]
    if status != "ABSTAIN" and index_or_none is not None:
        status = "REVIEW" if (index_or_none >= 25 or changed) else "MONITOR"
        safety["status"] = status
    summary_text, llm_meta = narrative(summary, index_or_none if safety["safe_to_display_index"] else None, status, evidence)
    metadata = {"rule_version": "demo-rules-v1", "slm_modes": sorted({n.get("mode", "rules") for n in note_extracts}), "llm": llm_meta, "change_detected": changed, "change_reasons": change_reasons, "score_kind": "demo_signal_index_not_clinical_probability"}
    analysis_id = uid("analysis")
    with connect() as con:
        con.execute("INSERT INTO analyses(id,patient_id,signal_index,status,summary,evidence_json,safety_json,metadata_json,created_at) VALUES(?,?,?,?,?,?,?,?,?)",
                    (analysis_id, patient_id, index_or_none if safety["safe_to_display_index"] else None, status, summary_text, json.dumps(evidence), json.dumps(safety), json.dumps(metadata), now_iso()))
    audit(patient_id, "analysis.completed", "analysis_workflow", "ok" if status != "ABSTAIN" else "abstain", {"analysis_id": analysis_id, "status": status, "evidence_count": len(evidence), "slm_modes": metadata["slm_modes"]})
    return {"id": analysis_id, "patient_id": patient_id, "signal_index": index_or_none if safety["safe_to_display_index"] else None, "status": status, "summary": summary_text, "evidence": evidence, "safety": safety, "metadata": metadata, "timeline_summary": summary, "created_at": now_iso()}


@app.get("/api/patients/{patient_id}/analyses")
def list_analyses(patient_id: str):
    require_patient(patient_id)
    with connect() as con:
        rows = con.execute("SELECT * FROM analyses WHERE patient_id=? ORDER BY created_at DESC", (patient_id,)).fetchall()
    output = []
    for r in rows:
        item = dict(r)
        for field in ("evidence_json", "safety_json", "metadata_json"):
            item[field.replace("_json", "")] = json_load(item.pop(field), {})
        output.append(item)
    return {"analyses": output}


@app.post("/api/analyses/{analysis_id}/review", status_code=201)
def review_analysis(analysis_id: str, payload: ReviewCreate):
    with connect() as con:
        row = con.execute("SELECT patient_id FROM analyses WHERE id=?", (analysis_id,)).fetchone()
        if not row:
            raise HTTPException(status_code=404, detail="Analysis not found")
        patient_id = row["patient_id"]
        review_id = uid("review")
        con.execute("INSERT INTO reviews(id,analysis_id,outcome,reviewer_label,comment,created_at) VALUES(?,?,?,?,?,?)",
                    (review_id, analysis_id, payload.outcome, payload.reviewer_label, payload.comment, now_iso()))
    audit(patient_id, "analysis.reviewed", "human_review", details={"analysis_id": analysis_id, "review_id": review_id, "outcome": payload.outcome})
    return {"id": review_id, "analysis_id": analysis_id, "outcome": payload.outcome, "created_at": now_iso()}


@app.get("/api/patients/{patient_id}/audit")
def get_audit(patient_id: str):
    require_patient(patient_id)
    with connect() as con:
        rows = con.execute("SELECT * FROM audit_events WHERE patient_id=? ORDER BY created_at DESC LIMIT 200", (patient_id,)).fetchall()
    events = []
    for r in rows:
        item = dict(r)
        item["details"] = json_load(item.pop("details_json", "{}"), {})
        events.append(item)
    return {"events": events}


FRONTEND_DIR = Path(__file__).resolve().parents[2] / "frontend"
app.mount("/assets", StaticFiles(directory=str(FRONTEND_DIR)), name="frontend-assets")

@app.get("/", include_in_schema=False)
def frontend_home():
    return FileResponse(FRONTEND_DIR / "index.html")
