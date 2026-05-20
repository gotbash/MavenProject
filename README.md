# Temporary GM Signal Validation Log

This repository includes a lightweight exporter for writing recent signal rows
from BigQuery into a Google Sheet for short-term validation and audit.

## Script

- Path: `scripts/export_signals_to_google_sheet.py`
- Purpose: fetch latest rows from `agent_outputs.signals` (or configured table),
  apply trust/actionability rules, and append only unseen rows.

## Configuration

1. Copy config template:

```bash
cp .env.example .env
```

2. Fill required values in `.env`:

- `GOOGLE_SHEET_ID`
- `SHEET_NAME`
- `BIGQUERY_PROJECT_ID`
- `BIGQUERY_DATASET`
- `BIGQUERY_TABLE`

Optional values:

- `AUTO_CREATE_TABS=true` (create destination tab(s) if missing)
- `WRITE_RUN_LOG=true` (append run summary row to run log tab on live runs)
- `RUN_LOG_SHEET_NAME=Run Log`
- `SIGNALS_LIMIT=200`
- `SIGNALS_PRINT_SAMPLE=5`

## Install dependencies

```bash
python3 -m pip install -r scripts/requirements-gm-signal-export.txt
```

## Makefile commands

- Dry run:

```bash
make signals-dry-run
```

- Live run:

```bash
make signals-live
```

Optional extra args for either command:

```bash
make signals-dry-run SIGNALS_EXTRA_ARGS="--input-jsonl scripts/sample_signals.jsonl --source-table agent_outputs.signals"
```

## Manual commands

Dry run (no writes, prints sample):

```bash
python3 scripts/export_signals_to_google_sheet.py --dry-run --limit 200 --print-sample 5
```

Live run:

```bash
python3 scripts/export_signals_to_google_sheet.py --limit 200 --print-sample 3
```

Local sample dry run (no BigQuery/Sheets auth required):

```bash
python3 scripts/export_signals_to_google_sheet.py \
  --dry-run \
  --input-jsonl scripts/sample_signals.jsonl \
  --source-table agent_outputs.signals \
  --print-sample 5
```

## Scheduling options

### Server cron (hourly)

```bash
0 * * * * cd /workspace && /usr/bin/env bash -lc 'set -a; source /workspace/.env; set +a; make signals-live'
```

### Server cron (daily at 06:00 UTC)

```bash
0 6 * * * cd /workspace && /usr/bin/env bash -lc 'set -a; source /workspace/.env; set +a; make signals-live'
```

### GitHub Actions (scheduled)

Add a workflow at `.github/workflows/signals-export.yml` with cron, then run:

```yaml
name: Signals Export
on:
  schedule:
    - cron: "0 * * * *"
  workflow_dispatch:

jobs:
  export:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v4
      - uses: actions/setup-python@v5
        with:
          python-version: "3.12"
      - run: python -m pip install -r scripts/requirements-gm-signal-export.txt
      - run: make signals-live
        env:
          GOOGLE_SHEET_ID: ${{ secrets.GOOGLE_SHEET_ID }}
          SHEET_NAME: ${{ secrets.SHEET_NAME }}
          BIGQUERY_PROJECT_ID: ${{ secrets.BIGQUERY_PROJECT_ID }}
          BIGQUERY_DATASET: ${{ secrets.BIGQUERY_DATASET }}
          BIGQUERY_TABLE: ${{ secrets.BIGQUERY_TABLE }}
          AUTO_CREATE_TABS: "true"
          WRITE_RUN_LOG: "true"
```

If your signal pipeline has a post-run hook, invoking `make signals-live` there is
preferred over cron.

## Service-account permission checklist

Use a service account (or ADC principal) with:

1. **BigQuery API enabled** on the GCP project.
2. **Google Sheets API enabled** on the GCP project.
3. BigQuery permissions:
   - `roles/bigquery.jobUser` on project (to run query jobs)
   - `roles/bigquery.dataViewer` on dataset/table
4. Google Sheet access:
   - Share the target spreadsheet with the service account email as **Editor**.
5. Credentials available at runtime:
   - `GOOGLE_APPLICATION_CREDENTIALS=/path/to/service-account.json`
   - or workload identity / ADC configured for the runtime.

## Duplicate prevention

- Reads existing `source_row_id` values from sheet column **P**.
- Unique key strategy:
  - Uses source `source_row_id`/`signal_id` when present.
  - Falls back to deterministic hash of stable signal fields.
- Existing keys are skipped on reruns.

## Trusted vs untrusted logic

- **REVENUE_DROP**
  - Trusted (`trusted_flag=TRUE`) when source metrics are present.
  - Untrusted when source metric fields are missing.
- **SALES_CRASH chat label + canonical REVENUE_DROP**
  - Adds note: `Valid signal; mislabeled by chat/router taxonomy`.
- **Profit Control / Negative Margin**
  - If ASIN-level fee allocation is missing/not ready:
    - `trusted_flag=FALSE`
    - `trust_reason=UNTRUSTED: Profit Control/Negative Margin without ASIN-level fee allocation`
    - `actionability=Backlog / validate before action`

## Optional tab automation

- `AUTO_CREATE_TABS=true`: creates `SHEET_NAME` tab if missing.
- `WRITE_RUN_LOG=true`: appends summary rows to `RUN_LOG_SHEET_NAME` tab.
- Run log row fields:
  - `run_at`, `source_table`, `fetched_rows`, `new_rows`, `skipped_duplicates`,
    `appended_rows`, `dry_run`, `limit`, `status`, `notes`.

## Output columns written to Google Sheet

1. logged_at
2. signal_date
3. canonical_type
4. chat_label
5. store
6. marketplace
7. severity
8. trusted_flag
9. trust_reason
10. trigger_reason
11. yesterday_value
12. baseline_value
13. drop_pct
14. impact_per_day
15. source_table
16. source_row_id
17. asin
18. sku
19. actionability
20. owner
21. status (`New` by default)
22. clickup_task_url
23. notes
