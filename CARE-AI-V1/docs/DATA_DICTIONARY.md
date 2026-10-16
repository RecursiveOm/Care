# CARE-AI V1 Data Dictionary

All timestamps are ISO-8601. All seeded values are synthetic. Numeric units must be canonicalized before analysis.

| Field | Type | Meaning |
|---|---|---|
| `patient_id` | string UUID-like ID | Stable internal ID; not a real identifier |
| `observation_id` | string UUID | Unique measurement/event ID |
| `type` | enum/string | `heart_rate`, `spo2`, `respiratory_rate`, `temperature`, `systolic_bp`, `diastolic_bp` |
| `value` | number | Validated numeric value |
| `unit` | string | `bpm`, `%`, `C`, or `mmHg` based on type |
| `observed_at` | ISO timestamp | When measurement happened |
| `ingested_at` | ISO timestamp | When app stored it |
| `source` | string | `demo`, `manual`, or approved source label |
| `quality_flag` | enum | `valid`, `suspect`, `missing` |
| `baseline_center` | number/null | Median from prior values for that type |
| `delta_from_baseline` | number/null | Latest value minus baseline center |
| `signal_index` | integer/null | Demonstration-only 0–100 index; not clinical probability |
| `status` | enum | `MONITOR`, `REVIEW`, `ABSTAIN` |
| `evidence_refs` | array | IDs/snippets linking the result to source observations or note phrases |
| `slm_mode` | enum/string | `ollama`, `rules`, or `fallback` |
| `llm_mode` | enum/string | `disabled`, `used`, or `fallback` |

## Demonstration thresholds

The current rules are software examples, not clinical thresholds. Do not interpret a status as a diagnosis, severity estimate, or treatment recommendation. Before any valid study, select an outcome with qualified clinicians, select an appropriate dataset, split by patient/time to prevent leakage, evaluate calibration and subgroup performance, and run prospective review.
