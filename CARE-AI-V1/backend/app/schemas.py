from datetime import datetime, timezone
from typing import Literal
from pydantic import BaseModel, Field, field_validator

ObservationType = Literal["heart_rate", "spo2", "respiratory_rate", "temperature", "systolic_bp", "diastolic_bp"]
UNITS = {
    "heart_rate": "bpm", "spo2": "%", "respiratory_rate": "breaths/min",
    "temperature": "C", "systolic_bp": "mmHg", "diastolic_bp": "mmHg"
}
BOUNDS = {
    "heart_rate": (20, 250), "spo2": (50, 100), "respiratory_rate": (4, 80),
    "temperature": (25, 45), "systolic_bp": (40, 300), "diastolic_bp": (20, 200)
}

class PatientCreate(BaseModel):
    display_name: str = Field(min_length=1, max_length=80)
    data_kind: Literal["synthetic", "deidentified"] = "synthetic"

    @field_validator("display_name")
    @classmethod
    def trim_name(cls, v):
        return v.strip()

class ObservationCreate(BaseModel):
    type: ObservationType
    value: float
    unit: str = Field(min_length=1, max_length=20)
    observed_at: datetime | None = None
    source: str = Field(default="manual", max_length=40)
    source_event_id: str | None = Field(default=None, max_length=120)

    @field_validator("unit")
    @classmethod
    def unit_must_match_type(cls, v, info):
        typ = info.data.get("type")
        if typ and v.strip() != UNITS[typ]:
            raise ValueError(f"Unit for {typ} must be {UNITS[typ]}")
        return v.strip()

    @field_validator("value")
    @classmethod
    def plausible_value(cls, v, info):
        typ = info.data.get("type")
        if typ:
            lo, hi = BOUNDS[typ]
            if not lo <= v <= hi:
                raise ValueError(f"{typ} must be within demo input bounds {lo}..{hi}; suspect values require a governed review path")
        return v

    @field_validator("observed_at")
    @classmethod
    def timestamp_timezone(cls, v):
        if v is not None and v.tzinfo is None:
            raise ValueError("observed_at must include a timezone")
        return v

class NoteCreate(BaseModel):
    note_text: str = Field(min_length=1, max_length=4000)
    created_at: datetime | None = None

    @field_validator("note_text")
    @classmethod
    def trim_note(cls, v):
        v = v.strip()
        if not v:
            raise ValueError("note_text cannot be blank")
        return v

class ReviewCreate(BaseModel):
    outcome: Literal["accepted_for_review", "monitor", "false_alarm_demo", "insufficient_data"]
    reviewer_label: str = Field(default="demo-reviewer", min_length=1, max_length=80)
    comment: str = Field(default="", max_length=500)

class AnalysisRequest(BaseModel):
    force: bool = False


def now_iso() -> str:
    return datetime.now(timezone.utc).isoformat()
