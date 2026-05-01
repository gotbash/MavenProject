#!/usr/bin/env python3
"""
Stage C.1.2 GM Dashboard Profit Control manual-flow QA.

This script intentionally drives only the browser UI. It uses the dashboard's
existing /hooks/task-create flow and never calls ClickUp, n8n, BigQuery, or any
other service directly.

Required environment variables:
  DASHBOARD_URL
  DASHBOARD_USER
  DASHBOARD_PASS
"""

from __future__ import annotations

import json
import os
import re
import sys
from datetime import datetime, timezone
from pathlib import Path
from typing import Any
from urllib.parse import unquote

from playwright.sync_api import Error, Page, TimeoutError, expect, sync_playwright


AVOID_ASINS = {
    "B0BTT1N8XK",
    "B0CH8XCTG4",
    "B0CMQQTVFS",
    "B08QCFJ7JC",
    "B07B89ZJX1",
}

QA_NOTE_INITIAL = "Manual QA note — Stage C.1.2 approval test."
QA_NOTE_CHANGED = "Manual QA note — Stage C.1.2 approval test. Dirty reset check."
ARTIFACT_ROOT = Path("qa/artifacts")


def require_env(name: str) -> str:
    value = os.environ.get(name, "").strip()
    if not value:
        raise RuntimeError(f"Missing required environment variable: {name}")
    return value


def decode_row(raw: str) -> dict[str, Any]:
    try:
        return json.loads(unquote(raw))
    except Exception as exc:  # pragma: no cover - diagnostic path
        raise RuntimeError(f"Could not decode task row payload: {raw!r}") from exc


def looks_like_uk(row: dict[str, Any]) -> bool:
    values = [
        str(row.get("marketplace", "")),
        str(row.get("store_id", "")),
        str(row.get("country", "")),
        str(row.get("marketplace_code", "")),
    ]
    return any(v.upper() in {"UK", "GB", "GBR"} or "UK" in v.upper() for v in values)


def choose_task_button(page: Page) -> tuple[Any, dict[str, Any]]:
    page.locator(".pc-task-btn").first.wait_for(state="visible", timeout=30000)
    buttons = page.locator(".pc-task-btn")
    candidates: list[tuple[Any, dict[str, Any]]] = []

    for idx in range(buttons.count()):
        button = buttons.nth(idx)
        raw = button.get_attribute("data-row")
        if not raw:
            continue
        row = decode_row(raw)
        asin = str(row.get("asin", "")).strip()
        if not asin or asin in AVOID_ASINS:
            continue
        candidates.append((button, row))

    if not candidates:
        raise RuntimeError("No Profit Control + Task candidates found outside the avoid-ASIN list.")

    for button, row in candidates:
        if looks_like_uk(row):
            return button, row

    # The request prefers UK rows if possible; keep the script useful if the
    # current dashboard snapshot has no UK candidate outside the avoid list.
    return candidates[0]


def find_task_button_for_row(page: Page, asin: str, issue_type: str) -> Any:
    buttons = page.locator(".pc-task-btn")
    for idx in range(buttons.count()):
        button = buttons.nth(idx)
        raw = button.get_attribute("data-row")
        if not raw:
            continue
        row = decode_row(raw)
        if str(row.get("asin", "")).strip() != asin:
            continue
        if str(row.get("issue_type", "")).strip() != issue_type:
            continue
        return button
    raise RuntimeError(f"Could not find duplicate-check row for ASIN={asin} issue={issue_type}")


def assert_no_dashboard_js_errors(errors: list[str]) -> None:
    if errors:
        joined = "\n".join(f"- {err}" for err in errors)
        raise AssertionError(f"Browser console/page JavaScript errors were observed:\n{joined}")


def extract_task_identity(text: str) -> tuple[str, str]:
    task_url = ""
    task_id = ""

    url_match = re.search(r"https?://\S+", text)
    if url_match:
        task_url = url_match.group(0).rstrip(").,")

    signal_match = re.search(r"Signal:\s*(\S+)", text)
    if signal_match:
        task_id = signal_match.group(1)

    if not task_id and task_url:
        task_id = task_url.rstrip("/").split("/")[-1]

    return task_id, task_url


def open_profit_control(page: Page) -> None:
    page.goto(require_env("DASHBOARD_URL"), wait_until="domcontentloaded")
    page.locator('.nav-item[data-page="profitcontrol"]').click()
    page.locator("#page-profitcontrol").wait_for(state="visible", timeout=30000)
    page.locator(".pc-task-btn").first.wait_for(state="visible", timeout=30000)


def run() -> int:
    dashboard_url = require_env("DASHBOARD_URL")
    dashboard_user = require_env("DASHBOARD_USER")
    dashboard_pass = require_env("DASHBOARD_PASS")

    run_id = datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%SZ")
    artifact_dir = ARTIFACT_ROOT / f"stage-c1-2-{run_id}"
    artifact_dir.mkdir(parents=True, exist_ok=True)
    preview_png = artifact_dir / "preview-modal.png"
    success_png = artifact_dir / "success-modal.png"

    js_errors: list[str] = []
    asin_used = ""
    task_id = ""
    task_url = ""

    with sync_playwright() as playwright:
        browser = playwright.chromium.launch(headless=True)
        context = browser.new_context(
            http_credentials={"username": dashboard_user, "password": dashboard_pass},
            viewport={"width": 1440, "height": 1100},
            base_url=dashboard_url,
        )
        page = context.new_page()
        page.on("console", lambda msg: js_errors.append(msg.text) if msg.type == "error" else None)
        page.on("pageerror", lambda exc: js_errors.append(str(exc)))

        open_profit_control(page)

        first_button, row = choose_task_button(page)
        asin_used = str(row.get("asin", "")).strip()
        issue_type = str(row.get("issue_type", "")).strip()
        first_button.scroll_into_view_if_needed()
        first_button.click()

        modal = page.locator("#pc-task-modal")
        expect(modal).to_be_visible()
        create_button = page.locator("#pc-btn-create")
        expect(create_button).to_be_disabled()

        page.locator("#pc-tf-notes").fill(QA_NOTE_INITIAL)
        page.locator("#pc-btn-preview").click()

        preview_box = page.locator("#pc-modal-preview-box")
        expect(preview_box).to_be_visible(timeout=30000)
        for expected in [
            "Title",
            "Issue type",
            "Store",
            "ASIN",
            "Confidence",
            "Assignee",
            "Priority",
            "Due",
            "List",
            "Tags",
            "Notes handling: will be added as first ClickUp comment",
            "Full Description / Task Brief",
        ]:
            expect(preview_box).to_contain_text(expected)

        approval = page.locator("#pc-modal-approval")
        expect(approval).to_be_visible()
        expect(create_button).to_be_disabled()
        modal.screenshot(path=str(preview_png))

        approval.check()
        expect(create_button).to_be_enabled()

        page.locator("#pc-tf-notes").fill(QA_NOTE_CHANGED)
        expect(approval).not_to_be_checked()
        expect(create_button).to_be_disabled()
        expect(page.locator("#pc-task-modal-msg")).to_contain_text(
            "Fields changed — please preview again before creating."
        )

        page.locator("#pc-btn-preview").click()
        expect(preview_box).to_be_visible(timeout=30000)
        expect(preview_box).to_contain_text("Notes handling: will be added as first ClickUp comment")
        expect(approval).to_be_visible()
        expect(approval).not_to_be_checked()
        approval.check()
        expect(create_button).to_be_enabled()

        # Exactly one successful create attempt is made here.
        create_button.click()
        expect(preview_box).to_contain_text("Task Created", timeout=30000)
        success_text = preview_box.inner_text(timeout=5000)
        task_id, task_url = extract_task_identity(success_text)
        modal.screenshot(path=str(success_png))

        modal.locator(".btn-ghost", has_text="Cancel").click()
        expect(modal).not_to_be_visible()

        # Re-open the same ASIN + issue once to verify dedupe. This submits the
        # same approved create flow once more; expected result is duplicate with
        # existing task details, not creation of a second task.
        open_profit_control(page)
        duplicate_button = find_task_button_for_row(page, asin_used, issue_type)
        duplicate_button.scroll_into_view_if_needed()
        duplicate_button.click()
        expect(modal).to_be_visible()
        page.locator("#pc-tf-notes").fill(QA_NOTE_INITIAL)
        page.locator("#pc-btn-preview").click()
        expect(preview_box).to_be_visible(timeout=30000)
        page.locator("#pc-modal-approval").check()
        expect(create_button).to_be_enabled()
        create_button.click()
        expect(preview_box).to_contain_text("Already exists", timeout=30000)
        duplicate_text = preview_box.inner_text(timeout=5000)
        if task_url:
            assert task_url in duplicate_text, "Duplicate response did not include the original task URL."

        assert_no_dashboard_js_errors(js_errors)

        context.close()
        browser.close()

    summary = {
        "asin_used": asin_used,
        "issue_type": issue_type,
        "task_id": task_id,
        "task_url": task_url,
        "preview_screenshot": str(preview_png),
        "success_screenshot": str(success_png),
        "js_error_count": len(js_errors),
    }
    print(json.dumps(summary, indent=2))
    return 0


if __name__ == "__main__":
    try:
        raise SystemExit(run())
    except (AssertionError, Error, TimeoutError, RuntimeError) as exc:
        print(f"QA FAILED: {exc}", file=sys.stderr)
        raise SystemExit(1)
