# HR Absentee Follow-up Call AI Analytics

Syncs AI-analysed HR follow-up call logs from Google Sheets into Postgres and
serves an analytics API plus a React dashboard.

## Layout

```
backend/
  service/          sheet sync, models, preprocessing, sub-reason themes
  api/              FastAPI app, shared filters, routers
frontend/           Vite + React dashboard
alembic/            migrations
```

## Data flow

1. `sync_sheet_to_postgres()` upserts the worksheet into `call_logs`
   (deduplicating repeated sheet `id`s, which Postgres rejects in one upsert).
2. `refresh_preprocess_call_log()` mirrors `call_logs` into
   `preprocess_call_log`, **dropping rows with no `google_drive_link`**.
3. Both run on every sync: the API's background worker (every
   `SYNC_INTERVAL_SECONDS`), `POST /sync/trigger`, and the CLI script.

## Running it

```bash
cp .env.example .env          # then fill in DB + Google credentials
uv sync
uv run alembic upgrade head
uv run uvicorn backend.api.main:app --reload      # API on :8000

cd frontend && npm install && npm run dev         # dashboard on :5173
```

The dev server proxies `/api` to `127.0.0.1:8000`, so the browser stays
same-origin and CORS never applies. Set `VITE_API_BASE` to point elsewhere.

One-off sync without the API:

```bash
uv run python -m backend.service.sheets_sync_service
```

## API

Interactive docs at `/docs`. **Every route below is served under `/api`**
(e.g. `/api/hr-dashboard`); the app also serves the built `frontend/dist` at
`/`, so one uvicorn process hosts both.

| Group | Endpoints |
|---|---|
| Dashboard | `GET /hr-dashboard` (composite, one round trip), plus `/call-activity`, `/effectiveness`, `/monthly-trend`, `/cumulative`, `/category-trends`, `/md-insights`, `/sub-reasons`, `/commitment`, `/intimation-compliance`, `/risk-analysis` |
| Analytics | `/analytics/overview`, `/breakdown/{dimension}`, `/trend`, `/hourly`, `/risk-matrix`, `/employees`, `/filters` |
| Records | `/preprocess-call-logs`, `/call-logs` |
| Sync | `GET /sync/status`, `POST /sync/trigger` |

### Filters

Every analytics endpoint shares one filter set (`backend/api/filters.py`):
`scope`, `month`, `date_from`/`date_to`, `category`, `risk_level`,
`commitment`, `intimation`, `valid_discussion`, `ai_analysis_confidence`,
`analysis_status`, `call_type`, `client_number`, `emp_number`,
`min_duration`/`max_duration`, `search`. The multi-value ones are repeatable
(`?category=A&category=B`).

**`scope` selects which rows every widget counts, and defaults to
`total_calls`:**

| `scope` | Counts | Rows |
|---|---|---|
| `total_calls` *(default)* | every call HR dialled | all of `call_logs` |
| `all` | answered *and* recorded, so the AI had something to analyse | `google_drive_link IS NOT NULL` |
| `valid_only` | valid discussions (the original dashboard spec) | the above + `valid_discussion = 'Yes'` |

Everything reads `call_logs`; the narrower scopes reproduce
`preprocess_call_log` by its own mirror rule rather than joining to it (the
mirror is *exactly* `call_logs` with a link — same ids, same values). Scope is
therefore a `WHERE` clause, not a table switch.

Under `total_calls` the unanswered calls carry no AI analysis at all, so they
land in each breakdown's **`Unspecified`** bucket — deliberately, so the charts
show HR's real workload rather than only the analysed slice. `/effectiveness`
keeps reporting the valid share of its own denominator, and `/call-activity`
ignores `scope` entirely (see below).

## Notes on the data

Worth knowing before extending this:

- **About half of `call_logs` was never answered.** Those rows have no
  `google_drive_link` and almost all have `duration = 0`, so the mirror drops
  them and the AI never sees them — they carry no `category`, `risk_level`,
  `commitment` or `valid_discussion`. That is why they can only ever show up as
  `Unspecified`, and why `scope` exists.
- **`/call-activity` ignores `scope` and every analysis filter**, honouring only
  the date range. It reports dialled / answered / unanswered / analysed off raw
  `call_logs`, so it stays a fixed denominator for "how much did HR actually
  work". Applying the analysis filters there would drop every unanswered call
  and report a 100% answer rate. `answered` is `duration > 0`; `analysed` is the
  recorded subset, and the two differ by a handful of answered-but-unrecorded
  calls.
- **`emp_*` is the HR caller, not the absentee.** The absentee employee is
  `client_number`; `/analytics/employees` keys on it and is the repeat-contact
  watchlist.
- **`note`, `emp_code`, `emp_tags`, `crm_status`, `reminder_date`,
  `reminder_time` and `lead_id` are null in every row.** Department and Location
  filters cannot be built until the source sheet carries them.
- **`sub_reason` is free-text AI narrative** (~440 distinct values in 716 rows),
  so it is folded into keyword themes by
  `backend/service/sub_reason_themes.py` rather than charted raw. Unmatched text
  lands in `Other / Unclassified` so totals always reconcile.
- `call_date` is an ISO `YYYY-MM-DD` string, so range filters compare
  lexicographically. `call_time` is mostly `HH:MM:SS` but a few rows are
  `HH:MM`, which the hour extraction handles.
