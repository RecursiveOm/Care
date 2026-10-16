# Copy-paste prompt: build CARE-AI V1 using SLM-first routing

You are a senior full-stack engineer and ML systems architect. Build a working first version of **CARE-AI — Agentic Longitudinal Patient Intelligence & Early-Warning Platform** from the included project specification. The goal is a low-cost, auditable prototype that uses **small language models (SLMs) for the few text tasks that need language understanding**, classical algorithms for numeric work, and a larger LLM only as an optional non-authoritative wording helper.

## Non-negotiable design principles

1. **Build something runnable, not a mockup.** Deliver every source file, dependency manifest, `.env.example`, migrations/schema initialization, test, Docker config, and a precise run guide. Do not leave TODOs, fake API responses, placeholder buttons, or pseudocode in core paths.
2. **SLM-first, not LLM-first.** Monitoring, normalization, unit checks, baseline calculation, trends, feature building, rules, safety checks, audit, database access and API validation must be deterministic Python. Do not send those tasks to any language model.
3. **Local SLM note extraction.** Integrate a configurable local Ollama model for structured extraction of explicitly mentioned symptom/sign phrases from clinical notes. Use schema-constrained JSON output if the runtime supports it. Prompt the model to extract only statements actually supported by note text. Verify every extracted phrase against the input or retain its exact source span; reject unsupported results. If Ollama/model is missing or times out, automatically use a deterministic local extractor and report the chosen mode in metadata. Never make SLM availability a requirement for starting the app.
4. **LLM is optional and isolated.** A larger LLM may rephrase a *compact, de-identified, structured evidence bundle* into clinician-readable wording. It is disabled by default, needs explicit env configuration, cannot set risk score/status, cannot create clinical facts, and must have a deterministic template fallback. Do not send names, IDs, raw notes, or other direct identifiers to a remote provider. Never make cloud inference mandatory.
5. **No false claims.** With no labeled clinical dataset, do not claim a trained clinical prediction model or use the word “probability” for a hand-built score. Call it a demo signal index. Document that thresholds are illustrative, not guideline-derived. The prototype is not a diagnostic device and must not be used for real clinical decisions.
6. **Human authority.** CARE-AI surfaces evidence and a proposed review priority only. No diagnosis, prescriptions, treatment instructions, autonomous clinical actions, or patient-facing medical advice.
7. **Evidence and safety.** Every analysis must link to the observations and baseline changes that generated its findings. Use deterministic data-quality checks. Return `ABSTAIN` if input data is insufficient, inconsistent, or processing fails; never fabricate a score.
8. **Cost control.** Do not add a vector database, Kubernetes, multiple microservices, LangGraph, GPU-only models, or paid hosted APIs unless they are genuinely required for the initial working slice. Build a modular monolith and leave clear extension interfaces.
9. **Security.** Use synthetic/de-identified demo records by default. Validate payloads, cap note length, keep secrets in `.env`, exclude `.env` and data files from version control, limit CORS to local origins, audit important events without copying entire notes into audit records, and make limitations explicit. A local demo login is not real production authentication; do not claim otherwise.

## Required first-version stack

- Frontend: responsive HTML/CSS/vanilla JavaScript dashboard served by FastAPI; no Node/npm dependency in V1.
- Backend: Python 3.11+ + FastAPI + Pydantic.
- Persistence: SQLite for V1 with schema initialization and a clear repository/service boundary. Provide a PostgreSQL migration path in docs, not as a day-one dependency.
- Language models: local Ollama adapter for an SLM (configurable small Qwen/Llama-family model); optional OpenAI-compatible LLM adapter behind an interface and disabled by default.
- Numeric analytics: Python statistics; optionally scikit-learn only after a synthetic training/evaluation demonstration is clearly labelled synthetic. Never present synthetic evaluation as clinical evidence.
- Tests: pytest API and service tests; include cases for no data, duplicate event, missing values, unsupported extracted terms, SLM offline, LLM disabled, safety abstention, and audit creation.
- Deployment: local development first; optional Docker Compose.

## Core workflow

1. Ingest a patient observation or note and validate its schema, value, unit, timestamp and source.
2. Persist it and record an audit event.
3. Retrieve the patient's longitudinal timeline and calculate a personal baseline from available prior observations.
4. Run deterministic change detection. If nothing meaningful changed, log and show monitoring; avoid model calls.
5. If text exists, optionally run local SLM extraction. Return each finding with a source phrase; use deterministic fallback on failure.
6. Compute a transparent demo signal index from explicitly documented rules; never call it a clinical risk probability.
7. Build evidence records tied to observation IDs/baseline deltas.
8. Run the safety gate. Return `MONITOR`, `REVIEW` or `ABSTAIN` with reason codes. The gate can block a score when data is inadequate.
9. Optionally rephrase a de-identified evidence summary with a larger LLM. The result cannot modify numeric fields, findings or state.
10. Return an explanation, model/provider metadata, evidence IDs, safety status and trace/audit information to the dashboard.
11. Let a clinician/reviewer record a review outcome. The application must not perform clinical actions.

## User interface requirements

- A professional, responsive dashboard showing patients, current synthetic vitals, timeline, baseline deltas, signal index explicitly labeled “demo only”, evidence snippets, note extraction mode, safety status, and audit trail.
- Forms to add a synthetic patient, add an observation, submit a note, seed a demo patient, run analysis, and record a human review outcome.
- Clear loading/error/empty states. No dead controls.
- Prominent banner: “Research prototype — synthetic data only; not for clinical decision-making.”

## API expectations

Implement typed, documented endpoints for health, patients, timeline, observations, notes, analysis, analysis history, review outcome and audit events. Use consistent JSON errors, stable identifiers and timestamped records. Support CORS for the local frontend only by default.

## Deliverables

- Complete folder tree and source code; no missing imports or undeclared dependencies.
- `README.md` and step-by-step `docs/RUN_GUIDE.md` for Windows PowerShell and macOS/Linux.
- `.env.example`, `.gitignore`, backend dependencies and static frontend assets, optional Dockerfile/Compose.
- Architecture diagram (Mermaid or ASCII), data dictionary, API examples and model-routing table.
- Automated tests plus a smoke-test checklist.
- A concise list of features that work, features intentionally deferred, cost tradeoffs and safety limitations.

## Acceptance tests — all must pass

1. Fresh clone/unzip can run without an API key or local model installed.
2. Backend `/api/health` succeeds and OpenAPI docs load.
3. Seed demo creates a synthetic patient, timeline, observations and audit events idempotently.
4. Add observation -> timeline shows it -> analysis runs -> result has evidence and safety metadata.
5. Empty/insufficient input yields `ABSTAIN`, not a fabricated numeric result.
6. If Ollama is unavailable, analysis succeeds with deterministic note extraction and exposes fallback metadata.
7. If Ollama is available, note-extraction adapter validates JSON and rejects output phrases not present in source text.
8. LLM disabled means no external LLM network request; enabling it only changes wording, never score/status.
9. Review outcomes persist and appear in audit history.
10. All unit/API tests pass, the static dashboard loads from the FastAPI root route, and exact commands are in the guide.

Build the implementation in small modules, run the automated tests, verify the FastAPI-hosted dashboard and its assets load, fix all failures, and only then summarize the final project. Do not claim to have run any check that was not actually run.
