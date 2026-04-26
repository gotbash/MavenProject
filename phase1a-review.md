# GM Dashboard — n8n Webhook Phase 1A Implementation Review

**Date:** 2026-04-26  
**Scope:** n8n webhook Phase 1A implementation package (10 checks)  
**Reviewer:** Claude Code  
**Verdict:** ❌ REJECT — 1 blocking defect (Check 6)

---

## Overall Result

| # | Check | Result |
|---|-------|--------|
| 1 | n8n port isolation | ⚠️ CONDITIONAL PASS |
| 2 | POST-only enforcement | ✅ PASS (test expectation wrong) |
| 3 | Origin / Referer check | ⚠️ PARTIAL PASS |
| 4 | Rate limiting + body size | ✅ PASS |
| 5 | Dry-run only | ✅ PASS |
| 6 | HTTP response codes | ❌ **FAIL — BLOCKING** |
| 7 | No external nodes | ✅ PASS |
| 8 | Dedup / idempotency | ✅ PASS (dry-run scope) |
| 9 | Rollback plan | ⚠️ CONDITIONAL PASS |
| 10 | No secrets in workflow | ✅ PASS |

**Required fixes before merge:**

| Priority | Fix |
|----------|-----|
| BLOCKING | Replace `Code` node terminal with `Respond to Webhook` node reading `_http_status` |
| HIGH | Correct Test 2 expected status: `405 → 403` (or add `return 405` to `limit_except` block) |
| MEDIUM | Verify `netfilter-persistent` is installed and enabled before deployment |
| LOW | Add nginx comment: Origin check is browser CSRF defence only, not API auth |

---

## Check 1 — n8n Port Isolation

**Result: ⚠️ CONDITIONAL PASS**

The iptables rule is structurally correct:

```bash
iptables -I DOCKER-USER -p tcp --dport 5678 -j DROP
iptables -I DOCKER-USER -p tcp --dport 5678 -s 127.0.0.1 -j ACCEPT
```

Inserting into `DOCKER-USER` is the right chain — it is evaluated before Docker's NAT rules and correctly blocks external access to port 5678 even when Docker publishes the port.

**Condition:** The rule is lost on reboot unless persisted. Verify:

```bash
dpkg -l netfilter-persistent iptables-persistent
systemctl is-enabled netfilter-persistent
```

If not installed:

```bash
apt install netfilter-persistent iptables-persistent
netfilter-persistent save
```

Without this, the port is re-exposed after every reboot.

---

## Check 2 — POST-Only Enforcement

**Result: ✅ PASS** (test expectation in the package is wrong)

nginx `limit_except GET POST` with the internal `deny all` correctly blocks other methods on the webhook path. The approach is sound.

**Test expectation bug:** The test plan expects HTTP `405 Method Not Allowed` for a DELETE request, but nginx `limit_except` returns `403 Forbidden`, not `405`. The fix is either:

- Correct the test expectation: `expected=405 → expected=403`
- Or add an explicit `return 405;` inside the `limit_except` block:

```nginx
location /webhook/gm-audit {
    limit_except POST {
        return 405;
    }
    proxy_pass http://127.0.0.1:5678;
}
```

Either option is acceptable. Mismatched test expectations cause CI to flag valid behaviour as a failure.

---

## Check 3 — Origin / Referer Check

**Result: ⚠️ PARTIAL PASS**

The nginx `map` block checking `$http_origin` is correctly structured for browser CSRF defence. However:

**Gap:** An empty `Origin` header is not blocked. curl and server-side callers send no `Origin` header by default, so the check is trivially bypassed:

```bash
curl -X POST https://dashboard.kbrands.co.uk/webhook/gm-audit \
  -d '{"asin":"B001"}' \
  # No Origin header → map returns the default → allowed
```

**Correct framing:** This is browser CSRF protection, not API authentication. The actual auth layer is nginx Basic Auth. Document this explicitly with a comment in the nginx config so future reviewers don't assume Origin is a security boundary:

```nginx
# Origin check: browser CSRF defence only.
# Server-side callers (curl, n8n internal) have no Origin and are authenticated
# via Basic Auth on the /api/ path. Do not treat this as an auth control.
map $http_origin $allowed_origin {
    default         "";
    "https://dashboard.kbrands.co.uk" "https://dashboard.kbrands.co.uk";
}
```

---

## Check 4 — Rate Limiting and Body Size

**Result: ✅ PASS**

```nginx
limit_req_zone $binary_remote_addr zone=webhook:10m rate=10r/m;
limit_req zone=webhook burst=5 nodelay;
client_max_body_size 64k;
```

10 requests/minute with burst of 5 is appropriate for a GM-triggered audit webhook. 64 KB body limit prevents oversized payloads. Both controls are correctly scoped to the webhook location block.

---

## Check 5 — Dry-Run Only

**Result: ✅ PASS**

The implementation correctly enforces dry-run by architecture: the workflow contains no BigQuery write nodes, no ClickUp nodes, and no HTTP Request nodes pointing to external services. There is no `dry_run` flag to accidentally toggle — absence of write nodes is the enforcement mechanism. This is the correct approach for Phase 1A.

Note: The `_dry_run` field in the Code node output is informational only and is never read by any downstream node. This is fine for Phase 1A. For Phase 1B (live writes), replace the Code node terminal with branching on this flag.

---

## Check 6 — HTTP Response Codes

**Result: ❌ FAIL — BLOCKING**

This is the blocking defect. The workflow uses `responseMode: "lastNode"` on the Webhook trigger node, combined with a terminal Code node that sets `_http_status` in its output JSON:

```javascript
// Code node (terminal)
return [{
  json: {
    status: 'ok',
    _http_status: 200,
    signals: results
  }
}];
```

**The defect:** `responseMode: "lastNode"` reads the last node's JSON output and returns it as the HTTP response body. It does **not** read `_http_status` or any field to set the HTTP status code. The HTTP status code is always `200 OK` regardless of what the Code node returns.

This means:
- A validation error (bad ASIN, missing field) → HTTP 200 with `{"status":"error"}` body
- An internal exception → HTTP 200 with error body (or empty body if unhandled)
- The caller cannot distinguish success from failure by status code

**Fix:** Replace the terminal Code node with a `Respond to Webhook` node (`n8n-nodes-base.respondToWebhook`). This node has an explicit `Respond With` → `JSON` mode and a `Response Code` field that actually sets the HTTP status:

```
[Code node] → [Respond to Webhook node]
                  Response Code: {{ $json._http_status }}
                  Response Body: {{ $json }}
```

Alternatively, branch on error/success before the Respond node:

```
[Code node] → [IF: status == 'error'] → [Respond to Webhook: 400]
                                      → [Respond to Webhook: 200]
```

With this fix, the Webhook trigger node should use `responseMode: "responseNode"` (not `"lastNode"`).

**Until this is fixed, monitoring and alerting based on HTTP status codes will not work correctly.**

---

## Check 7 — No External Nodes

**Result: ✅ PASS**

The workflow JSON contains no nodes of type:
- `n8n-nodes-base.httpRequest` pointing to external URLs
- `n8n-nodes-base.emailSend`
- `n8n-nodes-base.slack`
- `n8n-nodes-base.telegram`
- Any third-party integration node

All processing is contained within the Code node. Correct for Phase 1A.

---

## Check 8 — Dedup / Idempotency

**Result: ✅ PASS** (within dry-run scope)

The `$getWorkflowStaticData('global')` dedup check correctly prevents the same `(asin, signal_type)` pair from firing twice within the TTL window:

```javascript
const staticData = $getWorkflowStaticData('global');
const dedupeKey = `${asin}:${signal_type}`;
const lastFired = staticData[dedupeKey] || 0;
const ttlMs = 24 * 60 * 60 * 1000;

if (Date.now() - lastFired < ttlMs) {
  // skip — already fired within 24h
}
staticData[dedupeKey] = Date.now();
```

**Race condition note (Phase 1B):** `$getWorkflowStaticData` is not atomic. If two executions run concurrently (e.g., two parallel n8n workers), both may read `lastFired = 0` before either writes back, producing duplicate signals. For Phase 1A dry-run this is acceptable. For Phase 1B with live BigQuery writes, add the `NOT EXISTS` guard in the INSERT query (already present in `03_signal_detection.sql`) as the authoritative dedup layer.

---

## Check 9 — Rollback Plan

**Result: ⚠️ CONDITIONAL PASS**

The rollback steps are logically correct:

```bash
# 1. Disable workflow in n8n UI or via API
# 2. Remove nginx location block
nginx -t && systemctl reload nginx
# 3. Restore iptables if changed
iptables -D DOCKER-USER -p tcp --dport 5678 -s 127.0.0.1 -j ACCEPT
iptables -D DOCKER-USER -p tcp --dport 5678 -j DROP
```

**Condition:** The backup commands must be run **before** implementation, not included only in the rollback section. Specifically, the nginx config backup:

```bash
cp /etc/nginx/sites-available/gm-dashboard /etc/nginx/sites-available/gm-dashboard.bak.$(date +%Y%m%d)
```

must precede `nginx -t && systemctl reload nginx`. If the implementation is applied without a backup, rollback is dependent on git history or manual reconstruction. Add this as Step 0 in the implementation sequence.

---

## Check 10 — No Secrets in Workflow

**Result: ✅ PASS**

The workflow JSON contains no hardcoded credentials, API keys, tokens, or passwords. BigQuery credentials are resolved via the n8n credential store (OAuth2 service account), not inlined. The webhook path does not include a secret token in the URL — authentication relies on nginx Basic Auth, which is appropriate since the webhook is behind the `/api/` path.

**Note for awareness (not a Phase 1A defect):** The bq-proxy.py file reviewed earlier contains a hardcoded n8n JWT at line 1683:

```python
N8N_API_KEY = 'eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9...'
```

This is outside the Phase 1A scope but should be rotated and moved to `/etc/bq-proxy.env` before any external exposure.

---

## Required Fixes — Detailed

### Fix 1 (BLOCKING): Replace Code node terminal with Respond to Webhook node

In the n8n workflow editor:

1. Add a new node: `Respond to Webhook` (`n8n-nodes-base.respondToWebhook`)
2. Connect the terminal Code node output → Respond to Webhook
3. Configure Respond to Webhook:
   - **Respond With:** `JSON`
   - **Response Code:** `{{ $json._http_status }}`
   - **Response Body:** `{{ $json }}`
4. On the Webhook trigger node, change `responseMode` from `"lastNode"` to `"responseNode"`

For error branches, add a separate Respond to Webhook node after error-handling logic with the appropriate status code (400, 422, 500).

### Fix 2 (HIGH): Correct Test 2 status expectation

In the test plan, change:

```bash
# Before
curl -X DELETE .../webhook/gm-audit
# Expected: 405

# After
# Expected: 403
```

Or, if 405 is semantically preferred, add to nginx:

```nginx
location /webhook/gm-audit {
    limit_except POST {
        return 405;
    }
    ...
}
```

### Fix 3 (MEDIUM): Verify netfilter-persistent before deployment

Add to pre-deployment checklist:

```bash
dpkg -l netfilter-persistent iptables-persistent 2>/dev/null | grep -E "^ii"
systemctl is-enabled netfilter-persistent
# If not present:
apt install -y netfilter-persistent iptables-persistent
```

Run `netfilter-persistent save` after applying iptables rules.

### Fix 4 (LOW): Add nginx comment for Origin check

```nginx
# Origin header check: browser-only CSRF defence.
# Does not authenticate server-side callers (curl, internal services).
# API authentication is handled by Basic Auth on the /api/ prefix.
```

---

## Not a Defect — Notes for Phase 1B

| Item | Phase 1B Action |
|------|-----------------|
| `_dry_run` flag not read | Branch on flag before write nodes |
| `$getWorkflowStaticData` race | Use BigQuery `NOT EXISTS` as primary dedup |
| No ClickUp task creation | Add ClickUp node after validated signals |
| Hardcoded n8n JWT in bq-proxy.py | Rotate token; move to env file |
| CORS only HTTP origin | Add HTTPS origin; add OPTIONS preflight handler |

---

*End of Phase 1A Review*
