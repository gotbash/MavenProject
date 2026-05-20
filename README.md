# Temporary GM Signal Validation Log

This repository includes a lightweight exporter that copies recent signal rows
from BigQuery into Google Sheets for temporary validation and audit.

## Script

- Path: `scripts/export_signals_to_google_sheet.py`
- Source: BigQuery table configured via env vars
- Destination: Google Sheet tabs `SHEET_NAME` and `RUN_LOG_SHEET_NAME`

## Environment setup

1. Copy template:

```bash
cp .env.example .env
```

2. Fill `.env` values (no secrets are committed):

- `GOOGLE_SHEET_ID`
- `SHEET_NAME` (default template value: `Signal Log`)
- `RUN_LOG_SHEET_NAME` (default template value: `Run Log`)
- `BIGQUERY_PROJECT_ID`
- `BIGQUERY_DATASET`
- `BIGQUERY_TABLE` (default template value: `signals`)
- `GOOGLE_APPLICATION_CREDENTIALS` (path to service account JSON when applicable)
- `DEFAULT_LIMIT` (default: `200`)
- `SOURCE_TABLE` (default: `agent_outputs.signals`)

## Makefile commands

Install deps:

```bash
make signals-install
```

Dry run (sample JSONL):

```bash
make signals-dry-run
```

Live export (BigQuery -> Google Sheets):

```bash
make signals-live
```

## Manual commands

Required verification dry-run command:

```bash
python3 scripts/export_signals_to_google_sheet.py \
  --dry-run \
  --input-jsonl scripts/sample_signals.jsonl \
  --source-table agent_outputs.signals \
  --print-sample 5
```

Live command:

```bash
python3 scripts/export_signals_to_google_sheet.py --limit 200 --source-table agent_outputs.signals
```

## Scheduling instructions

### Server cron (hourly)

```bash
0 * * * * cd /workspace && /usr/bin/env bash -lc 'set -a; source /workspace/.env; set +a; make signals-live'
```

### Server cron (daily)

```bash
0 6 * * * cd /workspace && /usr/bin/env bash -lc 'set -a; source /workspace/.env; set +a; make signals-live'
```

### Optional GitHub Actions schedule

Use only if this repo should run exports via GitHub Actions.

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
      - run: make signals-install
      - run: make signals-live
        env:
          GOOGLE_SHEET_ID: ${{ secrets.GOOGLE_SHEET_ID }}
          SHEET_NAME: ${{ secrets.SHEET_NAME }}
          RUN_LOG_SHEET_NAME: ${{ secrets.RUN_LOG_SHEET_NAME }}
          BIGQUERY_PROJECT_ID: ${{ secrets.BIGQUERY_PROJECT_ID }}
          BIGQUERY_DATASET: ${{ secrets.BIGQUERY_DATASET }}
          BIGQUERY_TABLE: ${{ secrets.BIGQUERY_TABLE }}
          SOURCE_TABLE: ${{ secrets.SOURCE_TABLE }}
          DEFAULT_LIMIT: "200"
          GOOGLE_APPLICATION_CREDENTIALS: ${{ secrets.GOOGLE_APPLICATION_CREDENTIALS }}
```

## Service-account permission checklist

1. **BigQuery read access** to configured project/dataset/table:
   - `roles/bigquery.jobUser` (project)
   - `roles/bigquery.dataViewer` (dataset/table)
2. **Google Sheets edit access** to target spreadsheet.
3. If using a **service account**, share the spreadsheet with the service account
   email as **Editor**.
4. If using **ADC**:
   - Local dev: run `gcloud auth application-default login`
   - Server: set `GOOGLE_APPLICATION_CREDENTIALS=/path/to/service-account.json`
     or configure workload identity.

## Google Sheet behavior

- Creates `SHEET_NAME` tab if missing.
- Creates `RUN_LOG_SHEET_NAME` tab if missing.
- Writes headers when missing or incorrect.
- Freezes header row on both tabs.

### Run Log row (appended every run)

Columns:

1. `run_at`
2. `mode` (`dry_run` or `live`)
3. `source_table`
4. `fetched_rows`
5. `new_rows`
6. `duplicate_rows`
7. `trusted_rows`
8. `untrusted_rows`
9. `status` (`success` or `failed`)
10. `error_message`
11. `duration_seconds`

## Duplicate prevention

- Uses `source_row_id`/`signal_id` when present.
- Falls back to deterministic hash key when source ID missing.
- Existing keys are skipped on reruns.

## Trusted vs untrusted logic (preserved)

- `REVENUE_DROP` is trusted unless source metrics are missing.
- If `chat_label=SALES_CRASH` and canonical type is `REVENUE_DROP`, adds note:
  `Valid signal; mislabeled by chat/router taxonomy`.
- Profit Control / Negative Margin with missing ASIN-level fee allocation:
  `trusted_flag=FALSE`, actionability `Backlog / validate before action`.
- Default output status remains `New`.
- Actionability values remain:
  - `Actionable`
  - `Needs ClickUp lookup`
  - `Backlog / validate before action`
  - `Monitor only`
