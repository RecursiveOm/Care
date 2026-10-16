# CARE-AI V1 — Detailed Run Guide

## A. Before you start

Install **Python 3.11 or newer**. That is sufficient for the normal local setup; Node.js/npm are not required. Optional: Docker Desktop if you prefer Compose, and Ollama if you want local SLM note extraction. You do not need an LLM API key or a model download to run the basic version.

## B. Windows PowerShell: native setup

### 1. Unzip and open the project

Extract `CARE-AI-V1.zip`. Open PowerShell in the extracted `CARE-AI-V1` folder. Check Python:

```powershell
py --version
```

If `py` is not available, use `python --version` and replace `py` with `python` in commands below.

### 2. Install and start the application

```powershell
cd backend
py -m venv .venv
.\.venv\Scripts\Activate.ps1
python -m pip install --upgrade pip
pip install -r requirements.txt
Copy-Item .env.example .env
uvicorn app.main:app --reload --host 127.0.0.1 --port 8000
```

Keep the terminal open. If PowerShell blocks environment activation, use these commands instead:

```powershell
.\.venv\Scripts\python.exe -m pip install -r requirements.txt
.\.venv\Scripts\python.exe -m uvicorn app.main:app --reload --host 127.0.0.1 --port 8000
```

### 3. Open the dashboard

- Dashboard: `http://127.0.0.1:8000`
- API health: `http://127.0.0.1:8000/api/health`
- Interactive API docs: `http://127.0.0.1:8000/docs`

Click **Load demo patient**, choose **Run analysis**, then explore evidence, timeline, note extraction, review and audit events. All seeded records are synthetic. Add observations using the matching canonical units shown in the form.

## C. Enable a local SLM (optional)

This enables local phrase extraction for clinical notes. Keep the app in synthetic/de-identified data mode.

1. Install Ollama for your operating system.
2. In a separate terminal, pull a small model; Ollama's model library lists Qwen3.5 0.8B as one low-size option, but actual memory needs depend on the model build and machine:
   ```powershell
   ollama pull qwen3.5:0.8b
   ```
3. Verify it is available:
   ```powershell
   ollama list
   ```
   Ollama normally serves its local API at `http://localhost:11434`.
4. Edit `backend/.env`:
   ```dotenv
   CARE_AI_SLM_MODE=ollama
   CARE_AI_OLLAMA_BASE_URL=http://localhost:11434
   CARE_AI_SLM_MODEL=qwen3.5:0.8b
   ```
5. Stop/restart the CARE-AI backend. Submit a synthetic note. The extraction metadata shows whether Ollama was used. If the local service/model fails or times out, the app falls back to deterministic phrase matching and records that mode.

To use no model, set `CARE_AI_SLM_MODE=rules` and restart the backend.

## D. Optional larger LLM for wording only

This is disabled by default. V1 sends only a compact summary of counts, score, status and evidence types for rewording. It does not send raw note text, patient IDs, names or source phrases. Before enabling any remote provider, review the provider's data handling terms and use synthetic/de-identified data. Usage may incur charges.

Set these values in `backend/.env`:

```dotenv
CARE_AI_LLM_ENABLED=true
CARE_AI_LLM_BASE_URL=https://api.openai.com/v1
CARE_AI_LLM_API_KEY=replace_with_your_own_key
CARE_AI_LLM_MODEL=replace_with_an_available_model
```

Restart the backend. If settings are missing or the call fails, deterministic template wording is used. The LLM is not allowed to set score, status, evidence or clinical action. Never commit `.env` or share your API key.

## E. Run tests

From the project root:

```powershell
cd backend
pip install -r requirements-dev.txt
pytest -q
```

Expected: all tests pass. Use the error trace to investigate any failure rather than assuming the check passed.

## F. macOS/Linux

```bash
cd backend
python3 -m venv .venv
source .venv/bin/activate
python -m pip install --upgrade pip
pip install -r requirements.txt
cp .env.example .env
uvicorn app.main:app --reload --host 127.0.0.1 --port 8000
```

Then open `http://127.0.0.1:8000`. API docs are at `/docs`.

## G. Docker Compose option

Install and start Docker Desktop. From project root:

```bash
docker compose -f infra/docker-compose.yml up --build
```

Open `http://localhost:8000`; API docs are at `http://localhost:8000/docs`. Stop with `Ctrl+C`, then run `docker compose -f infra/docker-compose.yml down`. Data is stored in `backend/data/care_ai.db` through a mounted local folder. Ollama is not bundled because model weights can be large; with Docker Desktop the backend container usually needs `http://host.docker.internal:11434` to reach Ollama on the host.

## H. Common issues

- **`uvicorn` not recognized:** activate `.venv`, or run `python -m uvicorn app.main:app --reload --host 127.0.0.1 --port 8000`.
- **Python command not found:** install Python 3.11+ and reopen terminal; try `python` instead of `py`.
- **Dashboard fails to load:** confirm the backend terminal is running, and open `http://127.0.0.1:8000` rather than opening `index.html` as a local file.
- **Port 8000 already used:** stop the old app or change the port in the uvicorn command and use that same port in your browser.
- **Ollama connection error:** verify `ollama list`, model name and local service, or set `CARE_AI_SLM_MODE=rules`.
- **SLM output is odd:** extraction is non-authoritative and source-grounded phrases are checked against the input. On errors the app falls back to rules.
- **Reset demo DB:** stop the backend, back up `backend/data/care_ai.db` if needed, delete it, then restart. Demo seed can repopulate it. Never delete a database containing real records.

## I. Smoke-test checklist

- [ ] `/api/health` returns `ok`.
- [ ] `/docs` loads.
- [ ] Dashboard loads at `/`.
- [ ] Demo seed creates a patient and repeated seed does not duplicate observations.
- [ ] Timeline loads in date order.
- [ ] Invalid observation type/unit/value is rejected.
- [ ] Analyze returns evidence and safety metadata.
- [ ] Insufficient input returns `ABSTAIN`, not a fabricated score.
- [ ] Offline SLM uses fallback.
- [ ] LLM disabled is the default.
- [ ] Review appears in audit history.
- [ ] `pytest -q` passes.

## J. Scope reminder

V1 is not a medical device, clinical model, or production system. Before deployment, define a clinically meaningful target and labels, complete data governance and privacy/security review, implement authenticated role-based access, validate calibration/subgroups, and complete prospective evaluation with qualified clinical oversight.
