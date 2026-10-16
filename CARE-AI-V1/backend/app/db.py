from __future__ import annotations
import json
import os
import sqlite3
from pathlib import Path
from contextlib import contextmanager


def db_path() -> Path:
    value = os.getenv("CARE_AI_DB_PATH", "data/care_ai.db")
    path = Path(value)
    if not path.is_absolute():
        path = Path(__file__).resolve().parents[1] / path
    return path


@contextmanager
def connect():
    path = db_path()
    path.parent.mkdir(parents=True, exist_ok=True)
    con = sqlite3.connect(str(path), timeout=10, check_same_thread=False)
    con.row_factory = sqlite3.Row
    con.execute("PRAGMA foreign_keys = ON")
    try:
        yield con
        con.commit()
    except Exception:
        con.rollback()
        raise
    finally:
        con.close()


def init_db() -> None:
    with connect() as con:
        con.executescript("""
        CREATE TABLE IF NOT EXISTS patients (
            id TEXT PRIMARY KEY,
            display_name TEXT NOT NULL,
            created_at TEXT NOT NULL,
            data_kind TEXT NOT NULL DEFAULT 'synthetic'
        );
        CREATE TABLE IF NOT EXISTS observations (
            id TEXT PRIMARY KEY,
            patient_id TEXT NOT NULL REFERENCES patients(id) ON DELETE CASCADE,
            type TEXT NOT NULL,
            value REAL NOT NULL,
            unit TEXT NOT NULL,
            observed_at TEXT NOT NULL,
            ingested_at TEXT NOT NULL,
            source TEXT NOT NULL DEFAULT 'manual',
            quality_flag TEXT NOT NULL DEFAULT 'valid',
            source_event_id TEXT UNIQUE
        );
        CREATE INDEX IF NOT EXISTS idx_observations_patient_time ON observations(patient_id, observed_at);
        CREATE TABLE IF NOT EXISTS clinical_notes (
            id TEXT PRIMARY KEY,
            patient_id TEXT NOT NULL REFERENCES patients(id) ON DELETE CASCADE,
            note_text TEXT NOT NULL,
            created_at TEXT NOT NULL,
            extraction_mode TEXT,
            extracted_json TEXT
        );
        CREATE INDEX IF NOT EXISTS idx_notes_patient_time ON clinical_notes(patient_id, created_at);
        CREATE TABLE IF NOT EXISTS analyses (
            id TEXT PRIMARY KEY,
            patient_id TEXT NOT NULL REFERENCES patients(id) ON DELETE CASCADE,
            signal_index INTEGER,
            status TEXT NOT NULL,
            summary TEXT NOT NULL,
            evidence_json TEXT NOT NULL,
            safety_json TEXT NOT NULL,
            metadata_json TEXT NOT NULL,
            created_at TEXT NOT NULL
        );
        CREATE INDEX IF NOT EXISTS idx_analyses_patient_time ON analyses(patient_id, created_at);
        CREATE TABLE IF NOT EXISTS reviews (
            id TEXT PRIMARY KEY,
            analysis_id TEXT NOT NULL REFERENCES analyses(id) ON DELETE CASCADE,
            outcome TEXT NOT NULL,
            reviewer_label TEXT NOT NULL,
            comment TEXT NOT NULL DEFAULT '',
            created_at TEXT NOT NULL
        );
        CREATE TABLE IF NOT EXISTS audit_events (
            id TEXT PRIMARY KEY,
            patient_id TEXT NOT NULL REFERENCES patients(id) ON DELETE CASCADE,
            action TEXT NOT NULL,
            component TEXT NOT NULL,
            status TEXT NOT NULL,
            details_json TEXT NOT NULL DEFAULT '{}',
            created_at TEXT NOT NULL
        );
        CREATE INDEX IF NOT EXISTS idx_audit_patient_time ON audit_events(patient_id, created_at);
        """)


def row_dict(row):
    return dict(row) if row is not None else None


def json_load(value, fallback=None):
    try:
        return json.loads(value)
    except (TypeError, ValueError):
        return fallback if fallback is not None else {}
