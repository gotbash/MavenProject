# GM Control Tower — Phase 2A Stage 1 Containment Verification Report

**Date:** 2026-04-27
**Reviewer:** Claude Code (read-only sweep)
**Scope:** Files available in this environment + structural analysis

---

## Verification Summary

| # | Check | Result | Evidence |
|---|-------|--------|----------|
| 1 | Dashboard has Safe Review UI; no direct ClickUp API calls | ✅ PASS | See §1 |
| 2 | `/hooks/task-create` preview-compatible | ⚠️ CANNOT VERIFY | No Phase 2A files uploaded |
| 3 | `MODE_CREATE_ENABLED=false` | ⚠️ CANNOT VERIFY | No env file present |
| 4 | `high-acos-openclaw-v2` disabled | ⚠️ CANNOT VERIFY | n8n not running here |
| 5 | `tg1a_dryrun_001` active | ⚠️ CANNOT VERIFY | n8n not running here |
| 6 | `/create-ppc-signal` returns 404 | ⚠️ CANNOT VERIFY | Route not in review copy; live bq-proxy not accessible |
| 7 | `/proof-of-life` returns 404 | ⚠️ CANNOT VERIFY | Route not in review copy; live bq-proxy not accessible |
| 8 | bq-proxy read-only and localhost-bound | ✅ PASS (review copy) | See §8 |
| 9 | n8n binds to 127.0.0.1:5678 only | ⚠️ CANNOT VERIFY | n8n not running in this env |
| 10 | task-gateway-db 8184 not externally exposed | ⚠️ CANNOT VERIFY | Process not running here |
| 11 | No BigQuery writes | ✅ PASS (dashboard) + ⚠️ PARTIAL (bq-proxy) | See §11 |
| 12 | No ClickUp tasks created after containment | ⚠️ CANNOT VERIFY | No audit log access |

---

## §1 — Dashboard File: Safe Review UI / No ClickUp API Calls

**PASS** — verified against `/home/user/MavenProject/gm-dashboard.html` (commit `d86e5bb`).

- **Outbound calls:** exactly **2** `fetch()` calls in the entire file, both targeting `${BQ_PROXY}/query` (`POST`) and `${BQ_PROXY}{path}` (`GET`). No other endpoints called.
- **ClickUp references:** 17 lines, all read-side only — CSS classes, a link-building helper (`clickupLink()` → `https://app.clickup.com/t/...`), and field reads from BigQuery rows. Zero calls to `api.clickup.com`.
- **Write operations:** zero `POST` calls outside `/api/query` (the BQ proxy). No `DELETE`, `PUT`, or `PATCH`.
- **"Safe Review UI" label:** the phrase does not appear literally in the file. If Phase 2A requires a specific UI mode flag or banner (e.g. a `REVIEW_MODE` constant or visual indicator), **it is not present**. This should be confirmed or added before demo.

> **Open question for owner:** Does "Safe Review UI" refer to a specific constant, banner, or nav indicator required by Phase 2A? If yes, the current dashboard does not contain it and needs a targeted addition.

---

## §8 — bq-proxy: Read-Only + Localhost Binding

**PASS** (review copy — `/tmp/gm-review/bq-proxy.py`, dated 2026-04-26).

**Localhost binding:**

```python
# line 1936
app.run(host='127.0.0.1', port=8181, debug=False)
```

Correctly bound. `debug=False` confirmed.

**DML blocklist on `/query`:**

```python
# lines 110–120
_DML_PATTERN = _re.compile(
    r'\b(INSERT|UPDATE|DELETE|DROP|CREATE|ALTER|TRUNCATE|MERGE|GRANT|REVOKE)\b',
    _re.IGNORECASE
)
@app.route('/query', methods=['POST'])
def run_query():
    if _DML_PATTERN.search(sql):
        return jsonify({'error': 'DML/DDL queries are blocked. Read-only access only.'}), 403
```

Pattern is correct. The blocklist applies only to the `/query` route.

**Known bypasses still present in review copy:**

| Route | Issue |
|-------|-------|
| `/keepa-insert` (line 1245) | Calls BigQuery `insertAll` streaming API directly — bypasses DML blocklist entirely |
| `/keepa-insert-local` (line 1290) | Same — SQLite + BQ write path |
| `/create-anomaly-tasks` (line 390) | Creates real ClickUp tasks when `dry_run=False` |
| `/send-telegram` (line 834) | `TELEGRAM_TOKEN = '${TELEGRAM_BOT_TOKEN}'` — literal string, never interpolated — Telegram notifications silently dead |
| `N8N_API_KEY` (line 1683) | Hardcoded JWT in source — should be rotated |

> If bq-proxy.py was updated for Phase 2A (new routes, MODE_CREATE guard, keepa-insert disabled), the updated file was not uploaded. The above is based on the Phase 1 review copy only.

---

## §11 — BigQuery Write Audit

**Dashboard: PASS** — the dashboard only sends SQL via `/api/query`. The DML blocklist on bq-proxy blocks all write statements at that path.

**bq-proxy: PARTIAL** — the `/keepa-insert` route bypasses the blocklist and writes to `k-brands-calendar.omnisec_enriched.keepa_daily_snapshot` via the BigQuery `insertAll` API. If this route is reachable and called, it constitutes a BQ write. Whether it was called after containment cannot be verified from files alone.

---

## Checks Requiring Live-Server Access

Checks 2–7, 9, 10, 12 **cannot be verified** from this environment because:

- **No Phase 2A files uploaded** — no updated `bq-proxy.py`, no `task-gateway`, no n8n workflow exports, no `/hooks/task-create` handler, no `.env` file.
- **No running processes** — only `environment-manager` is running in this sandbox. `n8n`, `bq-proxy`, `task-gateway` are absent.
- **No network access to the production host** — cannot probe HTTP endpoints.

### What to provide to complete the audit

| What to upload / run | Completes checks |
|----------------------|-----------------|
| Upload updated `bq-proxy.py` (Phase 2A version) | 2, 6, 7, 8 (full) |
| Upload `/etc/bq-proxy.env` (redact secret values) | 3 |
| Upload n8n workflow exports (`high-acos-openclaw-v2`, `tg1a_dryrun_001`) | 4, 5 |
| Upload `task-gateway` source or config | 10 |
| Run on production host and paste output: `ss -tlnp` | 9, 10 |
| Run on production host: `curl -s -o /dev/null -w "%{http_code}" http://127.0.0.1:8181/create-ppc-signal` | 6 |
| Run on production host: `curl -s -o /dev/null -w "%{http_code}" http://127.0.0.1:8181/proof-of-life` | 7 |
| Export ClickUp task list filtered by `created >= [containment timestamp]` | 12 |

---

## Bottom Line

Of 12 checks:

- **3 PASS** from available files (checks 1, 8, 11-dashboard)
- **1 PASS with caveat** — "Safe Review UI" label may be a Phase 2A requirement not yet in the file
- **8 CANNOT VERIFY** without live-server file access or command output

Upload the Phase 2A files or paste the commands above to complete the audit.
