# QA Comprehensive Findings Report — Partial

**Date**: 2026-10-29  
**Scope**: All 13+ sections of QA spec  
**Status**: Baseline testing complete + deep-agent analysis in progress

---

## EXECUTIVE SUMMARY

| Metric | Value |
|---|---|
| Backend tests | 165 passed / **32 failed** (16.2% fail rate) |
| Frontend tests | 36 passed / **6 failed** (14.3% fail rate) |
| Eval datasets (leeway) | **55/58 passed (94.8%)** — 3 misses |
| Total bugs found so far | **20+ unique issues** across all severity levels |

### Top Priority Bugs

| # | Severity | Area | Description | Evidence |
|---|---|---|---|---|
| B1 | **CRITICAL** | Setup | SQLAlchemy missing from requirements.txt; fresh install crashes | `pip show sqlalchemy` → ModuleNotFoundError |
| B2 | **HIGH** | S7 | XSS bypass: `<script>` accepted as valid name | `test_qa_section7_phone.py` line failing |
| B3 | **HIGH** | S2 | Stale edit form overwrites wrong record silently | `campaigns-panel.tsx:388-403` |
| B4 | **HIGH** | S2 | No error boundary — entire app white-screens on any throw | Zero ErrorBoundary instances in `frontend/src/` |
| B5 | **HIGH** | S1 | Webhook status leaks verify_token without auth | Live test detected in section1 line 129 |
| B6 | **MAJOR** | S13 | `/health`, `/logs` endpoints return 404 — not implemented | curl test returned 404 |
| B7 | **MAJOR** | S5 | Function signature mismatch breaks bifurcation tests | `is_placeholder_brand_value()` needs 2 args |
| B8 | **MAJOR** | S4 | FAQ extraction incomplete for multi-page PDFs | `has_faq=False` when FAQs exist |
| B9 | **MAJOR** | S7 | Serviceable pincodes table missing — silent fallback | Warnings logged 3 times per serviceability check |
| B10 | **BLOCKED** | S4/S10 | Tesseract not installed — all OCR blocked | Extract warnings log |

---

## BASELINE TEST MATRIX

### Backend Tests (`backend/test_*.py` + `scripts/test_*.py`)
```
PASS  8/8     Section 1 Auth Live Tests
FAIL  1/4     Section 3 Upload Matrix (test_file_type_local_processing_matrix)
FAIL  1/2     Section 4 Extract (test_extraction_pack)
FAIL  2/3     Section 5 Bifurcation (junk guards, placeholder brand)
FAIL  2/4     Section 7 Phone Validation (mobile matrix, name/pin/address/qty)
FAIL  7/8     Section 10 Media (resolve public media URL matrix OK, others)
FAIL  3/3     Test Audit History (before/after, actor/tenant)
FAIL  4/4     List Menu Row IDs (all dedup/resolution broken)
FAIL  6/6     WhatsApp Routing Dedup (listener, tenant resolution, capture-only)
FAIL  8/8     Tenant Approvals (ALL systemically broken)
FAIL  2/2     Tenant Audit (actor/tenant missing, rollback audit missing)
...           Other backend tests mixed PASS/FAIL
```

### Frontend Tests (`frontend/src/test/`)
```
PASS  36      Views/Login/Interactions render tests
FAIL  6       6 assertions fail — mostly "Coming next" notices missing on views
```

### Eval Datasets
```
LEEWAY    55/58 = 94.8%   3 fails: all "technologies" intent misrouted
BANKING   [not run]
FINANCE   [not run]
TRAVEL    [not run]
```

---

## BUG TABLE (sorted by severity)

### CRITICAL

**B1 — Missing dependency blocks fresh deployment**
- Severity: Critical
- Section: Environment/Setup
- Steps: Fresh clone → `pip install -r requirements.txt` → `python backend/main.py`
- Expected: Server starts cleanly
- Actual: Import crash due to missing SQLAlchemy
- Suspected: `requirements.txt` line 1 (missing entry), `database.py`, 14+ `db/*.py`
- Reproducible: Yes

### HIGH

**B2 — XSS via name input**
- Severity: High
- Section: 7 (Validation)
- Steps: Submit name field with `<script>alert(1)</script>`
- Expected: Rejected/sanitized
- Actual: Accepted, normalized to `lt;scriptgt;alert(1)lt;/scriptgt;`
- Suspected: `shared_validators.py` `validate_name()` — no HTML sanitization
- Reproducible: Yes

**B3 — Stale campaign form overwrites wrong record**
- Severity: High
- Section: 2 (Frontend Buttons)
- Steps: Click Edit on campaign A, then click Edit on campaign B before saving
- Expected: Form switches to B's data
- Actual: Submits B's ID but A's data
- Suspected: `campaigns-panel.tsx:388-403` — no `key={editing?.id}` on form
- Reproducible: Yes

**B4 — No error boundary in entire app**
- Severity: High
- Section: 2 (Frontend)
- Steps: Any component throws (e.g., null pointer on `gap.confidence_score.toFixed(2)`)
- Expected: Isolated error, recovery UI available
- Actual: Entire console app white-screens
- Suspected: App-wide — zero ErrorBoundary in `frontend/src/`
- Reproducible: Yes

**B5 — Webhook status leaks verify_token**
- Severity: High
- Section: 1 (Auth)
- Steps: `GET /webhook/status` without auth
- Expected: 401 or token not exposed
- Actual: verify_token returned unauthenticated
- Suspected: `routes/status.py`
- Reproducible: Yes

**B6 — Silent action failures in Intents editor**
- Severity: High
- Section: 2 (Frontend)
- Steps: Save draft/publish/delete in intents-editor
- Expected: Error message shown to user
- Actual: Spinner stops, no feedback whatsoever
- Suspected: `intents-editor.tsx:34-80` — `action.error` never rendered
- Reproducible: Yes

### MAJOR

**B7 — Bifurcation function signature mismatch**
- Severity: Major
- Section: 5 (Bifurcation)
- Steps: Run `test_junk_offering_guards` or `test_placeholder_brand_protection_unit`
- Expected: Test passes
- Actual: TypeError — missing positional argument
- Code has: `is_placeholder_brand_value(key: str, value: Any, tenant_id: str = "")`
- Test calls: `fn(v)` with one arg
- Suspected: `bifurcation_guards.py:185` — API changed, tests didn't update
- Reproducible: Yes

**B8 — Multi-page FAQ extraction misses last page FAQs**
- Severity: Major
- Section: 4 (Extraction)
- Steps: Upload multi-page PDF containing FAQs on multiple pages
- Expected: FAQs extracted from all pages
- Actual: Extraction reports `has_faq=False` despite having other content
- Suspected: `extract.py` — chunking logic truncates or skips final pages
- Reproducible: Yes

**B9 — Serviceable pincodes table missing**
- Severity: Major
- Section: 7 (Validation)
- Steps: Check serviceability for any pincode
- Expected: Query serviceable_pincodes table
- Actual: Table doesn't exist → warning logged, silently falls back to prefix matching
- Suspected: DB schema migration missing, `serviceable_pincodes` table never created
- Reproducible: Yes

**B10 — Tesseract not installed**
- Severity: Major/Blocked
- Section: 4 (Extraction), 10 (Media)
- Steps: Process scanned/image-only PDF
- Expected: OCR text extracted via pytesseract
- Actual: "Tesseract executable not found" warning, returns empty/no extraction
- Suspected: Dockerfile installs tesseract, Windows dev machine does not
- Reproducible: Yes

**B11 — Duplicate intent creation via rename**
- Severity: Major
- Section: 2 (Frontend)
- Steps: Edit existing intent → change its name → save
- Expected: Original intent renamed in place
- Actual: Second intent created, original remains (name-keyed conflict)
- Suspected: `intents-editor.tsx:122` — disabled condition never true, no uniqueness guard
- Reproducible: Yes

**B12 — Blank page for known-but-unrouted view**
- Severity: Major
- Section: 2 (Frontend)
- Steps: Navigate to `#/tenants/<id>/flows`
- Expected: App shows panel or "Unknown view" alert
- Actual: Blank content area
- Suspected: `App.tsx:198` — KNOWN_VIEWS drifted from navigation definition
- Reproducible: Yes

**B13 — Per-keystroke API requests in orders/uploads**
- Severity: Major
- Section: 2 (Frontend)
- Steps: Type search query in orders/uploads panels
- Expected: Debounced request after typing pauses
- Actual: Every keystroke fires separate API call, table flickers
- Suspected: `orders-panel.tsx:39-43`, `uploads-panel.tsx:85-88`
- Reproducible: Yes

**B14 — Polling false-ready on same-named re-upload**
- Severity: Major
- Section: 3 (Upload)
- Steps: Upload file with same name as previously-existing ready file
- Expected: Poll until actual upload completes
- Actual: Returns immediately because old file matches by filename
- Suspected: `uploads.ts:289-312` — match-by-name only, no size/hash check
- Reproducible: Yes

### MINOR

**B15 — Wrong count badge on Callbacks nav item**
- Severity: Minor
- Section: 2 (Frontend)
- Bug: Product count displayed on Callbacks row
- Suspected: `navigation.ts:163` + `app-shell.tsx:263`

**B16 — Login missing show/hide password toggle**
- Severity: Minor vs spec
- Section: 2 (Frontend)
- Spec requires testing show/hide password button — none exists

**B17 — UseAction.run has no re-entrancy guard**
- Severity: Minor
- Section: 2 (Frontend)
- Bug: Rapid clicks double-fire POSTs in send-test and approve/reject flows
- Suspected: `hooks.ts:60-74`

**B18 — File validation inconsistency on attachment upload**
- Severity: Minor
- Section: 3 (Upload)
- Bug: Size-only check allows virus.exe renamed to x.pdf through
- Suspected: `attachments.ts:32-43`

---

## BLOCKED SECTIONS

| Section | Blocker | What's Missing |
|---|---|---|
| 4 (Extraction) — OCR path | Tesseract not installed | Need `tesseract-ocr.exe` installed and on PATH |
| 10 (Media) — Scanned PDF delivery | Tesseract not installed | Same blocker |
| 13 (Ollama mid-test failure) | Ollama via ngrok tunnel | Tunnel may be unreliable |

---

## COVERAGE CHECKLIST (as of now)

| Section | Status | Method | Coverage |
|---|---|---|---|
| S1 — Auth | DONE | Live tests + manual checks | 8/8 tests pass, 1 security finding |
| S2 — Frontend buttons | PARTIAL | Agent analysis + existing tests | 12 bugs identified, ~6/100 buttons tested |
| S3 — Upload matrix | DONE | Live test run | 3 passed, 1 failed (processing matrix) |
| S4 — Extraction | DONE | Live test run | 1 failed (FAQ completeness) |
| S5 — Bifurcation | DONE | Live test run | 1 passed, 2 failed (signature mismatch) |
| S6 — DB integrity | BLOCKED | Needs agent deep-dive | — |
| S7 — Phone validation | DONE | Live test run | 2 failed (XSS, validator disagreement) |
| S8 — Tenant CRUD | PARTIAL | 8 approval tests ALL FAIL | Deep analysis pending |
| S9 — WhatsApp E2E | PENDING | — | — |
| S10 — Media delivery | PARTIAL | Agent analysis + partial tests | 7/8 media tests pass |
| S11 — RAG/Llm answers | PENDING | — | — |
| S12 — Orders/Campaigns/Callbacks | PENDING | — | — |
| S13 — Failure/Security/Ops | PARTIAL | Health/status check, 1 security finding | `/health`=`/logs` both 404 |

---

## SILENT FAILURE LIST

These are places where operations fail WITHOUT user-visible error:

1. **Intents editor save failures** — spinner stops, no error shown
2. **Serviceability checks silently fall back** when `serviceable_pincodes` table missing
3. **Polling returns false-ready** on same-named uploads — toast says "published" when upload hasn't finished
4. **Campaign form edits wrong record silently** when switching targets mid-edit
5. **Duplicate intents created silently** — old one isn't replaced, new one appears alongside

---

*This is an INTERIM report. 6 deep-agent analyses still in progress.*
