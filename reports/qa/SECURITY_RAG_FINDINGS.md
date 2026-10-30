# Security + RAG Analysis — QA Sections 11 & 13

## SECURITY FINDINGS

### CRITICAL (Exploitable in production today)

**S-01: Live WhatsApp webhook accepts unauthenticated forged messages**
- File: `routing/webhook.py:819-950` (`receive_webhook`)
- Bug: No `X-Hub-Signature-256` verification of raw body. `body` read at line 821, never HMAC-checked. `sender_name` and `wa_id` come straight from payload.
- Impact: Attacker who knows the webhook URL can impersonate any customer, drive flows/orders/callbacks, make bot send WhatsApp replies to arbitrary numbers.
- Reproducible: Send POST with crafted JSON to webhook endpoint without signature.

**S-02: Any WhatsApp user can enumerate all tenants + reroute traffic globally**
- File: `routing/webhook.py:371-417` (`#tenant`, `#tenants`, `#switch` testing commands)
- Bug: No admin check. `#switch <slug>` writes global `set_active_test_tenant()` (line 410). One message from any customer switches live number to another company's bot. Command replies list ALL tenants (names, slugs, verticals — lines 377-390).
- Impact: Cross-tenant isolation break; trivially weaponized. All inbound traffic can be redirected to attacker-chosen tenant.
- Root cause of many tenant-fallback issues across other findings.

**S-03: Unauthenticated PII endpoints — anyone can pull customer chat histories**
- Files: `backend/routes/unified.py` (mounted at main.py:386, zero auth):
  - `GET /api/unified/context/{wa_id}` (:120)
  - `POST /api/unified/batch-context` (:349)
  - `GET /api/unified/export/chat-history?wa_id=` (:373)
  - `GET /api/unified/analytics` (:158)
- Also legacy: `GET /chat-history` (main.py:453-462) dumps `SELECT * FROM chat_history` (all tenants, 50 rows) no auth.
- Impact: Anyone can pull any customer's profile and full chat history.

**S-04: Path traversal in admin SPA fallback — serves arbitrary files from disk**
- File: `backend/main.py:486-492` (`serve_admin`)
- Bug: `os.path.join(ADMIN_BUILD_DIR, full_path)` from `{full_path:path}`, no containment check. `%2e%2f` sequences decoded before routing.
- Impact: Source code, `.env`/DB disclosure via `/admin/%2e%2e%2f...` paths.

**S-05: Dead-but-dangerous tenant webhook router — one import away from exploitation**
- File: `backend/routes/tenant_webhook.py` (not imported in main.py — currently dead)
- Bug: All six endpoints unauthenticated. Docstring says username/password are "for authentication" but `receive_tenant_webhook` (:61-139) never checks them — trusts `number` alone. `GET /api/tenant/tenants` (:269) leaks tenant roster. `get_tenant_from_request` (:402-408) compares plaintext tenant passwords with `==`.
- Risk: One import line → live tenant-impersonation API. Every 500 here echoes `str(e)`.

### MAJOR

**S-06: Stored-XSS-capable chat attachment upload**
- File: `backend/routes/admin.py:1210-1223` (`store_chat_attachment`)
- Bug: Keeps client-supplied extension (`safe_ext = ext if len(ext) <= 10`), so `.html`/`.svg`/`.xhtml` written into `chat_attachments`. Mounted publicly with no auth at main.py:426 (`/api/uploads/chat`). Served as `text/html` → executable content.
- Note: Document-upload allowlist correctly excludes HTML/SVG, but attachment path bypasses all of it. CSP `script-src 'self' 'unsafe-inline'` doesn't block same-origin script execution.

**S-07: IDOR in check_order_status tool**
- File: `kb/services/tools.py:112-138` + `kb/services/brain.py:955/992`
- Bug: `func_args` from LLM JSON, taken verbatim from conversation. User saying "check orders for 9123456789" calls `order_service.get_user_orders(phone_number)` with ANY phone → returns that person's last 5 orders (status, addresses).
- No binding of `phone_number` to session `wa_id`.

**S-08: Rate limiter exists but is NEVER wired**
- File: `backend/services/rate_limiter.py:34,41`
- Bug: `rate_limit_wa`/`rate_limit_ip` have ZERO call sites across repo. Live webhook and `/api/unified` have no inbound throttling. `defaultdict` key growth allows memory DoS if ever enabled.
- `kb/services/rate_limiter.py` is outbound Groq token-budget limiter, not request protection.

**S-09: Webhook replay vulnerability — no freshness window**
- File: `shared/tenancy/signing.py:41-45`, `MAX_SKEW_SECONDS = 300` (line 31) defined but never enforced.
- Bug: `verify_body` recomputes with caller-supplied timestamp, no freshness check. Captured signed payload replays forever.
- Also: `build_signed_request` (:48-82) POSTs to admin-configured URLs with no scheme/allowlist → SSRF surface.

**S-10: Sensitive data in audit log + JWT handling**
- File: `backend/main.py:291-335`
- Bug: Admin-mutation middleware stores full request bodies (`body_content`) for ALL `POST/PATCH/PUT/DELETE /api/admin*` — admin password/OTP/API-key changes persisted in cleartext in `audit_logs`.
- JWT decoded with `verify_exp: False` (line 317) — expired tokens accepted.
- Tokens accepted via `?token=` query param (auth.py:274) — leaks to access logs/proxies.
- Revocation lives in process-local `REVOKED_TOKENS` set (lost on restart).

### MINOR

- **S-11**: `/docs` + `/openapi.json` exposed in production (main.py:263-269)
- **S-12**: `download_remote_file` (admin.py:603-630) authenticated SSRF proxy with `follow_redirects=True`
- **S-13**: `update_customer_profile` builds SET clauses via f-string (database.py:187-190) — internal identifiers only but allowlist warranted
- **S-14**: Verify-token stored in webhook_logs (routing/webhook.py:804) — credential material in logs

## ERROR LEAKAGE PATTERN (~40 handlers echo internals)

| File | Count | Examples |
|---|---|---|
| `routes/unified.py` | 9 | `detail=str(e)` on all routes |
| `routes/send2_webhook.py` | 2 | Fail-open when credentials unset |
| `tenant_admin.py` | 11 | `detail=str(e)` on most endpoints |
| `routes/audit_logs.py` | 2 | `detail=f"Database error: {str(e)}"` — raw sqlite messages |
| `routes/tenants.py` | 4 | `detail=str(e)` |
| `routes/pdf_intake.py` | 1 | Internal error text to client |
| `routes/admin.py` | 1 | `"Failed to fetch remote file: {e}"` |
| `routes/callbacks.py` | 3 | Upstream error echoed |
| `tenant_files.py` | 2 | Server filenames leaked |
| `kb/tool results` | 3 | `str(e)` fed back into LLM prompt |

## CORS CONFIG
- Restrictive: `CORS_ORIGINS` from env; default placeholder prod domains + localhost origins. `allow_credentials=True` with explicit method/header list.
- Risk: Operational only — placeholder default means nothing matches in prod unless env is set.
- CSP weakens mitigation: `script-src 'self' 'unsafe-inline'`.

## SQL INJECTION RISK: LOW
- Consistent `?` placeholders throughout. f-string SQL interpolates only internally-controlled identifiers, user values parameter-bound.
- Residual: `LIKE ?` with unescaped `%`/`_` in LLM question = LIKE-wildcard behavior only.

## RAG/LLM FINDINGS

**R-01: Margin calculation uses wrong denominator + silent wrong data**
- File: `kb/services/tools.py:195-328`
- Formula: `margin = (MRP - price) / MRP * 100` — treats retail `price` as cost.
- Bug: If `mrp` absent, falls back to `price` → 0% margin confidently reported.
- Bug: `product.get("price", "0").replace("₹",...)` crashes if price is numeric (AttributeError) → `str(e)` leaked into LLM prompt → relayed to customer.
- Bug: Not tenant-scoped — falls through contextvar chain to default test tenant.

**R-02: Nutrition portion tool NOT tenant-scoped**
- File: `kb/services/tools.py:331-514`
- Query: `SELECT content FROM knowledge_base WHERE title LIKE '%Nutrition%' ORDER BY id LIMIT 1` — NO tenant filter. Answers tenant B with tenant A's nutrition doc.
- Hardcoded to "TrooGood product" in tool description.
- Portion hazard: When document lacks parseable piece weight, defaults to 100g/piece silently.
- Name matching has no score floor beyond shared words >0 — single word "chikki"-like match attaches wrong variant.

**R-03: Knowledge gap creation WORKS but KB index rebuild missing**
- Files: `backend/db/gaps.py:22-62`, `gaps.py:157-216`
- Works: Refusal paths write `unanswered_queries` with reason codes, dedup-throttled (10 min). Parameterized, tenant-stamped.
- Bug: `add_faq_from_gap` inserts into `knowledge_base` with `embedding_blob = None`, rebuilds only FAQ index (`faq_index.build(force=True)`, line 203). Never calls `rebuild_faiss_index()` — KB-side index won't see new answer until next upload/restart.

**R-04: Stale content after doc deletion — FAISS indexes NOT rebuilt**
- Files: `admin.py:633-649`, `tenant_files.py:327-358`
- Bug: Delete removes rows from `faq_dataset`/`knowledge_base` and disk file, but NEVER rebuilds `kb._kb_faiss_index`/`_kb_tenant_indexes` nor `faq_index`.
- Rebuilds only happen at startup, after upload, or via `remove_tenant_document` which invalidates only legacy per-tenant object.
- Impact: Deleted documents' chunks remain answerable from in-memory FAISS indexes until restart or unrelated upload.

**R-05: Fuzzy matching threshold TOO LOOSE**
- File: `kb/services/fuzzy_matcher.py:19-21`, scoring at line 69
- Declared thresholds fine (70/80/90), but `scores["name"] = similarity * 3.0` inflates to 0-300 scale. Raw name similarity of only 23.4 crosses `min_similarity=70`.
- Flat 85 for any ≥3-letter substring hit in category (lines 72-74), 75 in ingredients.
- `handle_fuzzy_correction` gates suggestions at 80 (after ×3 inflation ≈ 27% raw similarity) — expect frequent wrong "Did you mean" suggestions.
- `list_products(limit=200)` silently truncates large catalogs, not scoped by context.

**R-06: Guardrails against prompt injection — PARTIALLY HOLD**
- Files: `kb/services/brain.py:299-319`, `backend/faq/service.py:1338`
- Grounding rules are strong prompt text: anti-hallucination, refusal fallback.
- BUT: retrieved KB/FAQ chunks pasted into system prompt verbatim (brain.py:321-323). Malicious text in `faq_dataset`/`knowledge_base` can attempt instruction override.
- Tool loop caps rounds at 2, per-round calls at 10. XML-style fallback (brain.py:983-992) executes ANY tool name model writes in its content — same untrusted-arguments exposure.
- Confidence gating consistent: CE ≥0.30 primary, FAQ ≥0.25, KB ≥0.35.

**R-07: LLM plumbing details**
- Backend/services/llm.py: Ollama-only, no auth header, fixed seed 42, temp 0.7
- `ngrok-skip-browser-warning` header hints tunnel-exposed Ollama endpoint
- brain.py multi-providers to Groq/Mistral with env keys (correctly kept out of responses)
