# Temporary GM Signal Validation Log

This repository now includes a lightweight exporter for writing recent signal rows
from BigQuery into a Google Sheet for short-term validation/audit.

## Script

- Path: `scripts/export_signals_to_google_sheet.py`
- Purpose: fetch latest rows from `agent_outputs.signals` (or configured table),
  apply trust/actionability rules, and append only unseen rows to a Google Sheet.

## Required config

Set these environment variables before running:

```bash
export GOOGLE_SHEET_ID="your_google_sheet_id"
export SHEET_NAME="Signal Validation Log"
export BIGQUERY_PROJECT_ID="your_gcp_project"
export BIGQUERY_DATASET="agent_outputs"
export BIGQUERY_TABLE="signals"
```

## Install dependencies

```bash
python3 -m pip install -r scripts/requirements-gm-signal-export.txt
```

## Run manually

Dry run (no writes, prints sample rows):

```bash
python3 scripts/export_signals_to_google_sheet.py --dry-run --limit 200 --print-sample 5
```

Local sample dry run (no BigQuery/Sheets auth required):

```bash
python3 scripts/export_signals_to_google_sheet.py \
  --dry-run \
  --input-jsonl scripts/sample_signals.jsonl \
  --source-table agent_outputs.signals \
  --print-sample 5
```

Live write:

```bash
python3 scripts/export_signals_to_google_sheet.py --limit 200 --print-sample 3
```

For live write, the runtime must have:

- BigQuery access to `BIGQUERY_PROJECT_ID.BIGQUERY_DATASET.BIGQUERY_TABLE`
- Sheets write access to `GOOGLE_SHEET_ID` / `SHEET_NAME`
- Google Application Default Credentials or equivalent service account auth

## Schedule daily/hourly

Use cron (or any scheduler) to run repeatedly.

Hourly example:

```bash
0 * * * * cd /workspace && /usr/bin/env bash -lc 'source /path/to/env.sh && python3 scripts/export_signals_to_google_sheet.py --limit 500'
```

Daily example:

```bash
0 6 * * * cd /workspace && /usr/bin/env bash -lc 'source /path/to/env.sh && python3 scripts/export_signals_to_google_sheet.py --limit 1000'
```

If the signal pipeline has a post-run hook, invoke the script there for
"on-pipeline-run" behavior instead of cron.

## Duplicate prevention

- The script reads existing `source_row_id` values from sheet column **P**.
- Unique key strategy:
  - Uses source `source_row_id`/`signal_id` when present.
  - Falls back to deterministic hash of stable signal fields.
- Rows with existing keys are skipped, so reruns do not append duplicates.

## Trusted vs untrusted logic

- **REVENUE_DROP**
  - Trusted by default (`trusted_flag=TRUE`) if source metrics are present.
  - Marked untrusted when source metric fields are missing.
- **SALES_CRASH chat label + canonical REVENUE_DROP**
  - Adds note: `Valid signal; mislabeled by chat/router taxonomy`.
- **Profit Control / Negative Margin**
  - If ASIN-level fee allocation is missing/not ready, marks:
    - `trusted_flag=FALSE`
    - `trust_reason=UNTRUSTED: Profit Control/Negative Margin without ASIN-level fee allocation`
    - `actionability=Backlog / validate before action`

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
