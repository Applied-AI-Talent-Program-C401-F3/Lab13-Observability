# Dashboard + Evidence Guide

## What this UI covers

The React dashboard in `lab13-dashboard/` is wired to the FastAPI endpoint `GET /dashboard-data`.
It shows the 6 required panels from `docs/dashboard-spec.md`:

1. Latency P50 / P95 / P99
2. Traffic
3. Error rate with breakdown
4. Cost over time
5. Tokens in / out
6. Quality proxy

It also includes:
- evidence checklist from `docs/grading-evidence.md`
- alert rules from `config/alert_rules.yaml`
- incident prompts from `data/incidents.json`
- recent logs and PII redaction samples for screenshot prep

## Run steps

### Backend

```powershell
.\venv\Scripts\python.exe -m uvicorn app.main:app --reload
```

### Frontend

```powershell
cd lab13-dashboard
npm install
npm run dev
```

Open `http://127.0.0.1:5173`.

## Demo flow for evidence

1. Start FastAPI and React dashboard.
2. Run `python scripts/load_test.py --concurrency 5`.
3. Screenshot the dashboard with all 6 panels visible.
4. Screenshot the Recent Logs panel showing `correlation_id`.
5. Screenshot the PII Redaction Samples area.
6. Run `python scripts/inject_incident.py --scenario rag_slow`.
7. Run `python scripts/load_test.py --concurrency 5` again.
8. Screenshot latency panel before/after the incident.
9. Screenshot alert rules and runbook links in the dashboard.
10. If Langfuse keys are configured, capture:
   - trace list with at least 10 traces
   - one waterfall trace for root-cause explanation

## What to connect into the report

- `docs/blueprint-template.md`
- `docs/grading-evidence.md`
- dashboard screenshot path
- correlation ID screenshot path
- PII redaction screenshot path
- alert rules screenshot path
- Langfuse trace screenshot path

## Notes

- Default time window is 60 minutes.
- Dashboard updates in near realtime through `GET /dashboard-stream` with a 1 second push interval.
- Threshold lines use SLO objectives from `config/slo.yaml`.
