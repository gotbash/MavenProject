#!/usr/bin/env python3
"""
Temporary GM signal validation export from BigQuery to Google Sheets.

This script reads rows from a BigQuery signal table and appends new rows to a
Google Sheet for lightweight audit/validation. It is intentionally simple and
optimized for repeatable scheduled runs.
"""

from __future__ import annotations

import argparse
import datetime as dt
import hashlib
import json
import os
from decimal import Decimal
from typing import Any, Dict, Iterable, List, Optional, Sequence, Tuple

import google.auth
from google.api_core import exceptions as gcp_exceptions
from google.auth import exceptions as auth_exceptions
from google.cloud import bigquery
from googleapiclient.discovery import build


SHEET_COLUMNS: List[str] = [
    "logged_at",
    "signal_date",
    "canonical_type",
    "chat_label",
    "store",
    "marketplace",
    "severity",
    "trusted_flag",
    "trust_reason",
    "trigger_reason",
    "yesterday_value",
    "baseline_value",
    "drop_pct",
    "impact_per_day",
    "source_table",
    "source_row_id",
    "asin",
    "sku",
    "actionability",
    "owner",
    "status",
    "clickup_task_url",
    "notes",
]

ORDER_COLUMN_CANDIDATES: Sequence[str] = (
    "logged_at",
    "created_at",
    "updated_at",
    "signal_timestamp",
    "signal_time",
    "signal_date",
    "date",
)

SIGNAL_DATE_KEYS: Sequence[str] = ("signal_date", "date", "event_date")
CANONICAL_TYPE_KEYS: Sequence[str] = ("canonical_type", "signal_type", "type")
CHAT_LABEL_KEYS: Sequence[str] = ("chat_label", "router_label", "chat_type")
STORE_KEYS: Sequence[str] = ("store", "store_name", "merchant")
MARKETPLACE_KEYS: Sequence[str] = ("marketplace", "market")
SEVERITY_KEYS: Sequence[str] = ("severity", "priority")
TRIGGER_REASON_KEYS: Sequence[str] = ("trigger_reason", "reason", "description")
YESTERDAY_VALUE_KEYS: Sequence[str] = ("yesterday_value", "value_yesterday")
BASELINE_VALUE_KEYS: Sequence[str] = ("baseline_value", "baseline")
DROP_PCT_KEYS: Sequence[str] = ("drop_pct", "drop_percent", "drop_percentage")
IMPACT_PER_DAY_KEYS: Sequence[str] = ("impact_per_day", "daily_impact")
SOURCE_ROW_ID_KEYS: Sequence[str] = ("source_row_id", "id", "signal_id", "row_id")
ASIN_KEYS: Sequence[str] = ("asin",)
SKU_KEYS: Sequence[str] = ("sku",)
OWNER_KEYS: Sequence[str] = ("owner", "assigned_owner")
CLICKUP_KEYS: Sequence[str] = ("clickup_task_url", "clickup_url", "task_url")
NOTES_KEYS: Sequence[str] = ("notes", "note")

FEE_ALLOCATION_STATUS_KEYS: Sequence[str] = (
    "asin_fee_allocation_available",
    "asin_fee_allocation_status",
    "fee_allocation_status",
    "fee_allocation_ready",
    "asin_fee_allocation_wired",
)


def _require_env(name: str) -> str:
    value = os.getenv(name, "").strip()
    if not value:
        raise ValueError(f"Missing required environment variable: {name}")
    return value


def _optional_env(name: str, default: str = "") -> str:
    return os.getenv(name, default).strip()


def _get_first_present(row: Dict[str, Any], keys: Iterable[str], default: Any = "") -> Any:
    for key in keys:
        if key in row and row[key] not in (None, ""):
            return row[key]
    return default


def _normalize_value(value: Any) -> str:
    if value is None:
        return ""
    if isinstance(value, bool):
        return "TRUE" if value else "FALSE"
    if isinstance(value, (dt.datetime, dt.date, dt.time)):
        return value.isoformat()
    if isinstance(value, Decimal):
        return str(value)
    if isinstance(value, (list, dict, tuple)):
        return json.dumps(value, ensure_ascii=True, sort_keys=True)
    return str(value)


def _to_bool(value: Any) -> Optional[bool]:
    if isinstance(value, bool):
        return value
    if isinstance(value, str):
        normalized = value.strip().lower()
        if normalized in {"true", "t", "1", "yes", "y"}:
            return True
        if normalized in {"false", "f", "0", "no", "n"}:
            return False
    return None


def _is_empty_signal_source_data(row: Dict[str, Any]) -> bool:
    critical = (
        _get_first_present(row, YESTERDAY_VALUE_KEYS, default=None),
        _get_first_present(row, BASELINE_VALUE_KEYS, default=None),
        _get_first_present(row, DROP_PCT_KEYS, default=None),
    )
    return any(value in (None, "") for value in critical)


def _is_profit_control_or_negative_margin_signal(
    canonical_type: str, chat_label: str, trigger_reason: str
) -> bool:
    haystack = " | ".join([canonical_type, chat_label, trigger_reason]).upper()
    keywords = (
        "NEGATIVE_MARGIN",
        "NEGATIVE MARGIN",
        "PROFIT_CONTROL",
        "PROFIT CONTROL",
    )
    return any(keyword in haystack for keyword in keywords)


def _is_asin_fee_allocation_missing(row: Dict[str, Any]) -> bool:
    found_any_indicator = False
    for key in FEE_ALLOCATION_STATUS_KEYS:
        if key not in row:
            continue
        found_any_indicator = True
        raw_value = row[key]
        bool_value = _to_bool(raw_value)
        if bool_value is not None:
            return not bool_value

        text = str(raw_value).strip().lower()
        if text in {"ready", "available", "complete", "completed", "wired"}:
            return False
        if text in {
            "missing",
            "not available",
            "not_available",
            "pending",
            "not_wired",
            "unavailable",
        }:
            return True

    # If no indicator exists in source data, default to missing for safety.
    return not found_any_indicator


def _build_unique_key(row: Dict[str, Any], canonical_type: str, chat_label: str) -> str:
    source_row_id = _get_first_present(row, SOURCE_ROW_ID_KEYS, default="")
    if source_row_id:
        return _normalize_value(source_row_id)

    stable_fields = {
        "signal_date": _normalize_value(_get_first_present(row, SIGNAL_DATE_KEYS, default="")),
        "canonical_type": canonical_type,
        "chat_label": chat_label,
        "store": _normalize_value(_get_first_present(row, STORE_KEYS, default="")),
        "marketplace": _normalize_value(_get_first_present(row, MARKETPLACE_KEYS, default="")),
        "asin": _normalize_value(_get_first_present(row, ASIN_KEYS, default="")),
        "sku": _normalize_value(_get_first_present(row, SKU_KEYS, default="")),
        "trigger_reason": _normalize_value(_get_first_present(row, TRIGGER_REASON_KEYS, default="")),
        "yesterday_value": _normalize_value(_get_first_present(row, YESTERDAY_VALUE_KEYS, default="")),
        "baseline_value": _normalize_value(_get_first_present(row, BASELINE_VALUE_KEYS, default="")),
        "drop_pct": _normalize_value(_get_first_present(row, DROP_PCT_KEYS, default="")),
        "impact_per_day": _normalize_value(_get_first_present(row, IMPACT_PER_DAY_KEYS, default="")),
    }
    digest = hashlib.sha256(
        json.dumps(stable_fields, sort_keys=True, separators=(",", ":"), ensure_ascii=True).encode("utf-8")
    ).hexdigest()
    return f"hash_{digest[:24]}"


def _compute_trust_and_actionability(
    row: Dict[str, Any], canonical_type: str, chat_label: str, trigger_reason: str, clickup_task_url: str
) -> Tuple[bool, str, str, List[str]]:
    notes: List[str] = []
    trusted = True
    trust_reason = "Trusted by default policy"

    if canonical_type == "REVENUE_DROP":
        if _is_empty_signal_source_data(row):
            trusted = False
            trust_reason = "UNTRUSTED: Missing source metric values"
        else:
            trusted = True
            trust_reason = "Trusted: canonical REVENUE_DROP with required source metrics"

    if canonical_type == "REVENUE_DROP" and chat_label == "SALES_CRASH":
        notes.append("Valid signal; mislabeled by chat/router taxonomy")

    if _is_profit_control_or_negative_margin_signal(canonical_type, chat_label, trigger_reason):
        if _is_asin_fee_allocation_missing(row):
            trusted = False
            trust_reason = (
                "UNTRUSTED: Profit Control/Negative Margin without ASIN-level fee allocation"
            )
            actionability = "Backlog / validate before action"
            return trusted, trust_reason, actionability, notes

    severity = _normalize_value(_get_first_present(row, SEVERITY_KEYS, default="")).upper()

    if not trusted:
        actionability = "Monitor only"
    elif not clickup_task_url and severity in {"HIGH", "CRITICAL", "P1", "P0"}:
        actionability = "Needs ClickUp lookup"
    elif severity in {"LOW", "INFO"}:
        actionability = "Monitor only"
    else:
        actionability = "Actionable"

    return trusted, trust_reason, actionability, notes


def _bigquery_rows_to_dicts(rows: Iterable[Any]) -> List[Dict[str, Any]]:
    output: List[Dict[str, Any]] = []
    for row in rows:
        output.append(dict(row.items()))
    return output


def fetch_latest_signals(
    client: bigquery.Client, table_fqn: str, limit: int
) -> List[Dict[str, Any]]:
    table = client.get_table(table_fqn)
    schema_columns = {field.name for field in table.schema}

    order_column = next((column for column in ORDER_COLUMN_CANDIDATES if column in schema_columns), None)
    query = f"SELECT * FROM `{table_fqn}`"
    if order_column:
        query += f" ORDER BY `{order_column}` DESC"
    query += " LIMIT @limit"

    job_config = bigquery.QueryJobConfig(
        query_parameters=[bigquery.ScalarQueryParameter("limit", "INT64", limit)]
    )
    query_job = client.query(query, job_config=job_config)
    return _bigquery_rows_to_dicts(query_job.result())


def _sheet_service():
    credentials, _ = google.auth.default(
        scopes=[
            "https://www.googleapis.com/auth/spreadsheets",
            "https://www.googleapis.com/auth/bigquery",
            "https://www.googleapis.com/auth/cloud-platform",
        ]
    )
    return build("sheets", "v4", credentials=credentials, cache_discovery=False)


def ensure_sheet_header(service: Any, spreadsheet_id: str, sheet_name: str) -> None:
    header_range = f"{sheet_name}!A1:W1"
    response = (
        service.spreadsheets()
        .values()
        .get(spreadsheetId=spreadsheet_id, range=header_range)
        .execute()
    )
    values = response.get("values", [])
    if values and values[0]:
        return

    body = {"values": [SHEET_COLUMNS]}
    (
        service.spreadsheets()
        .values()
        .update(
            spreadsheetId=spreadsheet_id,
            range=header_range,
            valueInputOption="RAW",
            body=body,
        )
        .execute()
    )


def read_existing_keys(service: Any, spreadsheet_id: str, sheet_name: str) -> set:
    # source_row_id is column P (16th column).
    key_range = f"{sheet_name}!P2:P"
    response = (
        service.spreadsheets()
        .values()
        .get(spreadsheetId=spreadsheet_id, range=key_range)
        .execute()
    )
    values = response.get("values", [])
    return {row[0] for row in values if row and row[0]}


def append_rows(service: Any, spreadsheet_id: str, sheet_name: str, rows: Sequence[Sequence[str]]) -> int:
    if not rows:
        return 0

    body = {"values": rows}
    (
        service.spreadsheets()
        .values()
        .append(
            spreadsheetId=spreadsheet_id,
            range=f"{sheet_name}!A:W",
            valueInputOption="RAW",
            insertDataOption="INSERT_ROWS",
            body=body,
        )
        .execute()
    )
    return len(rows)


def build_sheet_row(row: Dict[str, Any], source_table: str, logged_at: str) -> List[str]:
    canonical_type = _normalize_value(_get_first_present(row, CANONICAL_TYPE_KEYS, default=""))
    chat_label = _normalize_value(_get_first_present(row, CHAT_LABEL_KEYS, default=canonical_type))
    trigger_reason = _normalize_value(_get_first_present(row, TRIGGER_REASON_KEYS, default=""))
    clickup_task_url = _normalize_value(_get_first_present(row, CLICKUP_KEYS, default=""))

    trusted, trust_reason, actionability, generated_notes = _compute_trust_and_actionability(
        row=row,
        canonical_type=canonical_type,
        chat_label=chat_label,
        trigger_reason=trigger_reason,
        clickup_task_url=clickup_task_url,
    )

    existing_notes = _normalize_value(_get_first_present(row, NOTES_KEYS, default=""))
    joined_notes = " | ".join([note for note in [existing_notes, *generated_notes] if note]).strip()

    source_row_id = _build_unique_key(row, canonical_type=canonical_type, chat_label=chat_label)

    return [
        logged_at,
        _normalize_value(_get_first_present(row, SIGNAL_DATE_KEYS, default="")),
        canonical_type,
        chat_label,
        _normalize_value(_get_first_present(row, STORE_KEYS, default="")),
        _normalize_value(_get_first_present(row, MARKETPLACE_KEYS, default="")),
        _normalize_value(_get_first_present(row, SEVERITY_KEYS, default="")),
        "TRUE" if trusted else "FALSE",
        trust_reason,
        trigger_reason,
        _normalize_value(_get_first_present(row, YESTERDAY_VALUE_KEYS, default="")),
        _normalize_value(_get_first_present(row, BASELINE_VALUE_KEYS, default="")),
        _normalize_value(_get_first_present(row, DROP_PCT_KEYS, default="")),
        _normalize_value(_get_first_present(row, IMPACT_PER_DAY_KEYS, default="")),
        source_table,
        source_row_id,
        _normalize_value(_get_first_present(row, ASIN_KEYS, default="")),
        _normalize_value(_get_first_present(row, SKU_KEYS, default="")),
        actionability,
        _normalize_value(_get_first_present(row, OWNER_KEYS, default="")),
        "New",
        clickup_task_url,
        joined_notes,
    ]


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Export latest signals from BigQuery to Google Sheets.")
    parser.add_argument(
        "--limit",
        type=int,
        default=200,
        help="Maximum number of latest BigQuery rows to inspect.",
    )
    parser.add_argument(
        "--dry-run",
        action="store_true",
        help="Preview rows without writing to Google Sheets.",
    )
    parser.add_argument(
        "--print-sample",
        type=int,
        default=5,
        help="Number of candidate rows to print for inspection.",
    )
    parser.add_argument(
        "--input-jsonl",
        type=str,
        default="",
        help="Optional JSONL file with signal rows (for local dry-run testing without BigQuery).",
    )
    parser.add_argument(
        "--source-table",
        type=str,
        default="",
        help="Optional source table name override, useful with --input-jsonl.",
    )
    return parser.parse_args()


def load_rows_from_jsonl(path: str, limit: int) -> List[Dict[str, Any]]:
    output: List[Dict[str, Any]] = []
    with open(path, "r", encoding="utf-8") as infile:
        for line in infile:
            stripped = line.strip()
            if not stripped:
                continue
            output.append(json.loads(stripped))
            if len(output) >= limit:
                break
    return output


def main() -> int:
    args = parse_args()

    spreadsheet_id = _optional_env("GOOGLE_SHEET_ID")
    sheet_name = _optional_env("SHEET_NAME")
    logged_at = dt.datetime.now(dt.timezone.utc).isoformat()

    if args.input_jsonl:
        table_fqn = args.source_table or "local.sample_signals"
        rows = load_rows_from_jsonl(path=args.input_jsonl, limit=args.limit)
    else:
        bq_project = _require_env("BIGQUERY_PROJECT_ID")
        bq_dataset = _require_env("BIGQUERY_DATASET")
        bq_table = _require_env("BIGQUERY_TABLE")
        table_fqn = f"{bq_project}.{bq_dataset}.{bq_table}"
        bq_client = bigquery.Client(project=bq_project)
        rows = fetch_latest_signals(client=bq_client, table_fqn=table_fqn, limit=args.limit)

    service = None
    existing_keys: set = set()
    can_read_sheet = bool(spreadsheet_id and sheet_name)
    if can_read_sheet:
        service = _sheet_service()
        ensure_sheet_header(service, spreadsheet_id=spreadsheet_id, sheet_name=sheet_name)
        existing_keys = read_existing_keys(service, spreadsheet_id=spreadsheet_id, sheet_name=sheet_name)
    elif not args.dry_run:
        raise ValueError(
            "GOOGLE_SHEET_ID and SHEET_NAME are required for live writes."
        )

    prepared_rows: List[List[str]] = []
    for row in rows:
        prepared = build_sheet_row(row=row, source_table=table_fqn, logged_at=logged_at)
        unique_key = prepared[15]
        if unique_key in existing_keys:
            continue
        prepared_rows.append(prepared)
        existing_keys.add(unique_key)

    summary = {
        "table": table_fqn,
        "fetched_rows": len(rows),
        "new_rows": len(prepared_rows),
        "dry_run": args.dry_run,
    }
    print(json.dumps(summary, indent=2, ensure_ascii=True))

    sample_count = min(args.print_sample, len(prepared_rows))
    if sample_count > 0:
        print("Sample rows to append:")
        for sample_row in prepared_rows[:sample_count]:
            sample_payload = dict(zip(SHEET_COLUMNS, sample_row))
            print(json.dumps(sample_payload, indent=2, ensure_ascii=True))
    else:
        print("No new rows to append.")

    if args.dry_run:
        print("Dry run complete: no writes performed.")
        if not can_read_sheet:
            print("NOTE: Sheet configuration missing; duplicate check used only in-memory keys for this run.")
        return 0

    appended = append_rows(
        service,
        spreadsheet_id=spreadsheet_id,
        sheet_name=sheet_name,
        rows=prepared_rows,
    )
    print(json.dumps({"appended_rows": appended}, indent=2, ensure_ascii=True))
    return 0


if __name__ == "__main__":
    try:
        raise SystemExit(main())
    except (
        ValueError,
        gcp_exceptions.GoogleAPICallError,
        auth_exceptions.DefaultCredentialsError,
    ) as exc:
        print(f"ERROR: {exc}")
        raise SystemExit(1) from exc
