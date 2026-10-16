# CARE-AI V1 — Cost-first longitudinal health monitoring prototype

> **Safety boundary:** This is an educational engineering prototype using synthetic/demo records. It is **not clinically validated**, does not diagnose or treat, and must not be used to make real clinical decisions. Its 0–100 value is a rule-based **demo signal index**, not a clinical probability. Use synthetic or properly de-identified data only.

## What V1 does

- Keeps a patient timeline of observations, notes, analysis results and audit events.
- Computes simple personal baselines from the patient's own history.
- Detects selected changes with deterministic Python rules.
- Runs a transparent demo signal index; it does not pretend to be a trained clinical model.
- Extracts literal symptom mentions from notes using a local Ollama SLM when configured; otherwise uses a deterministic local fallback.
- Can optionally ask an OpenAI-compatible LLM to rephrase a compact, de-identified evidence summary. This is disabled by default and never controls the score/status.
- Includes a responsive HTML/CSS/JavaScript dashboard served by FastAPI, SQLite persistence, REST API, synthetic demo patient, audit trail, tests and Docker option. **No Node.js install is needed.**

## Cost-first model routing

| Work | V1 default | Why |
|---|---|---|
| Validation, access checks, persistence | Python/FastAPI/SQLite | Deterministic and inexpensive |
| Baselines, deltas, trend checks | Python statistics/rules | No model call needed |
| Demo signal index | Transparent rules | No unsupported trained-model claim |
| Clinical-note phrase extraction | Optional local Ollama SLM (e.g. `qwen3.5:0.8b`) | Local inference; no API per-token charge |
| Explanation wording | Deterministic template; optional LLM | Higher-cost model is non-essential and cannot override logic |
| Evidence/source links and safety gate | Deterministic code | Traceable and testable |

## Quick start (Windows PowerShell)

1. Install **Python 3.11+**. Verify `py --version` or `python --version`.
2. Unzip the project and open PowerShell in `CARE-AI-V1`.
3. Run:
   ```powershell
   cd backend
   py -m venv .venv
   .\.venv\Scripts\Activate.ps1
   python -m pip install --upgrade pip
   pip install -r requirements.txt
   Copy-Item .env.example .env
   uvicorn app.main:app --reload --host 127.0.0.1 --port 8000
   ```
4. Open **http://127.0.0.1:8000** for the dashboard. API documentation: **http://127.0.0.1:8000/docs**.
5. Click **Load demo patient** and then **Run analysis**. Demo records are synthetic.

Full instructions, SLM setup, tests, Docker run steps and troubleshooting: `docs/RUN_GUIDE.md`.

## API summary

- `GET /api/health`
- `GET /api/patients`
- `POST /api/patients`
- `POST /api/demo/seed`
- `GET /api/patients/{id}/timeline`
- `POST /api/patients/{id}/observations`
- `POST /api/patients/{id}/notes`
- `POST /api/patients/{id}/analyze`
- `GET /api/patients/{id}/analyses`
- `POST /api/analyses/{id}/review`
- `GET /api/patients/{id}/audit`

`/docs` provides an interactive API explorer.

## Before any real-world evaluation

Do not use real identifiable patient data in this student prototype. A real implementation needs clinical governance, privacy/legal review, authenticated role-based access, a defined target and validated labelled dataset, prospective evaluation, calibration and subgroup analyses, clinician workflow testing, and formal risk management. The current demo score and example thresholds are intentionally not presented as clinically valid.
