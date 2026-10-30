# Menu Row IDs + Audit Analysis — QA Sections 5 & Audit

## MENU ROW IDS (4 failed, 1 passed in `backend/test_list_menu_row_ids.py`)

### M-01: Categories grouped by raw string — no case normalization
- **Expected**: "general" and "General" → 1 section
- **Actual**: 2 sections
- **Root cause**: Product-list builder groups by raw category string at `offerings_flow.py:363`. Set comprehension `{p.get("category") or "General" for p in products}` makes exact-match set — "General" ≠ "general".
- **File**: `offerings_flow.py:363` (set), `:370` (per-section filter)

### M-02: Category selector generates duplicate row IDs (`cat_general`, `cat_general`)
- **Expected**: 3 unique rows when categories merge ("General/general" → one row)
- **Actual**: 4 rows with duplicated ids: `['cat_general', 'cat_general', 'cat_savings', 'cat_other']`
- **Root cause**: Loop iterates DB categories verbatim. `_slugify(cat)` lowercases both "General" and "general" to `general` → two rows with same id `cat_general`. DB query uses `SELECT DISTINCT category` (SQLite BINARY collation = case-sensitive distinct).
- **File**: `offerings_flow.py:344-354` (id built at `:351`); `_slugify`/`_normalize` at `:119-132`; DB query at `db/products.py:226-236`

### M-03: Intended `_unique_categories` helper never implemented
- **Expected**: `offerings_flow._unique_categories(["General", "Savings"])` returns canonicalized list
- **Actual**: `AttributeError: module has no attribute '_unique_categories'`
- **Root cause**: Grep matches only test file — function was never written. Tap resolution done inline at `:643-655` but not as shared helper.
- **File**: Expected near `:130-133`; closest code at `:643-655`

### M-04: Transport layer has NO last-line dedupe of row IDs
- **Expected**: `send_whatsapp_list_menu` deduplicates before building API payload
- **Actual**: Duplicated ids reach the WhatsApp API → "(#131009) Duplicated row id" error
- **Root cause**: Sender copies ids verbatim with only truncation: `"id": str(row.get("id", ""))[:200]` — no `seen` set, no suffixing, no uniqueness enforcement. Neither `routing/whatsapp.py:310` nor `whatsapp_sender.py:289` nor `menu_service.py:63-105` checks uniqueness.
- **File**: `routing/whatsapp.py:298-315` (id copy at `:310`); `services/menu_service.py:82-105`

### M-05: PASSED — `test_product_rows_never_repeat_an_id`
- Product ids are `prod_<pk>` — auto-increment primary keys guarantee uniqueness. ✅

## AUDIT (3 failed out of ~14 total across 2 test files)

### A-01: `test_admin_role_change_records_before_after_and_changed_fields` — FAIL
- **Expected**: PATCH with `{"role": "admin"}` returns 200, writes audit event with role_before/role_after/changed_fields
- **Actual**: 409 Conflict — rejected by pre-mutation uniqueness check
- **Root cause**: Test-isolation leak. Route's "one admin per company" guard calls `count_tenant_admins("tenant-a", exclude_username="staff")`. Test patches only `audit.get_db` and `auth.get_db_context` but route accesses `get_db_context` through its own import binding (captured at `from database import get_db_context`), bypassing the patch. Query hits live DB which contains seed row `('admin-a','admin','tenant-a')`.
- **Good news**: The audit write logic IS correct — atomic UPDATE + `record_admin_audit_event` inside single transaction, full before/after tracking, actor populated. The bug is purely test isolation.
- **Files**: `routes/auth.py:738-740` (409 raise); `db/admins.py:97-108`; `test_audit.py:57-60`

### A-02: `test_tenant_creation_records_actor_and_tenant` — FAIL (stale API contract)
- **Expected**: `create_tenant()` creates tenant + writes `tenant_created` audit event
- **Actual**: `TypeError: create_tenant() missing 1 required positional argument: 'background_tasks'`
- **Root cause**: Signature evolved — `BackgroundTasks` added to fire auto-scrape/onboarding crawler after response (`routes/tenants.py:278-282`). Test calls endpoint directly without it.
- **Good news**: Audit write IS correctly implemented — tenant insert + audit event happen inside single `with get_db_context() as conn` block (:318-339), synchronous, atomic, actor/tenant populated. Background task does NOT carry the audit write.
- **Files**: `routes/tenants.py:278-282`; `test_tenant_audit.py:111-119`

### A-03: `test_tenant_creation_rolls_back_if_audit_insert_fails` — FAIL (same issue)
- Same `TypeError: background_tasks` as A-02.
- **Good news**: When properly invoked, atomicity IS sound — `get_db_context()` commits on clean exit, exception skips commit and discards the insert (:318-339, `db/core.py:181-190`).
- **Files**: `test_tenant_audit.py:121-130`

## SUMMARY OF DEFECTS

| Bug | Severity | Type | Impact |
|---|---|---|---|
| M-01: No case normalization | Medium | Code gap | Categories split into multiple sections |
| M-02: Duplicate cat_ row IDs | High | Missing dedupe | WhatsApp rejects entire message (#131009) |
| M-03: _unique_categories missing | Medium | Incomplete impl | Tap resolution doesn't share canonical form |
| M-04: No transport-layer dedupe | Critical | Missing safety net | WhatsApp API rejects messages with duplicate ids |
| A-01: Audit test fails due to live DB | Low | Test isolation | Audit logic itself is correct; test needs better isolation |
| A-02/A-03: Stale test API call | Low | API contract drift | Audit logic itself is correct; test signature outdated |
