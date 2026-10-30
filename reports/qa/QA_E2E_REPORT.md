# Final-Chatbot E2E QA Report

**Date:** 2026-10-29  
**Environment:** Windows; `python backend/main.py` on `:9000`; Vite `:5173`; DB via `ROUTING_DB_PATH` → `C:\Users\Leeway\Desktop\chatbot2\faq.db`  
**Rules followed:** no product-code fixes; throwaway simulator WA ids only; WhatsApp capture-only; real DB backed up to `reports/qa/faq.db.REAL-backup-*`  
**New test files written:** `backend/test_qa_section1_auth.py`, `test_qa_section3_upload_matrix.py`, `test_qa_section4_extract.py`, `test_qa_section5_bifurcation.py`, `test_qa_section7_phone.py`, `test_qa_section10_media.py`, `test_qa_section13_security.py`; pack in `qa_testdata/`

---

## 1. Summary (counts per section)

| Section | Total cases (approx) | PASS | FAIL | BLOCKED | Notes |
|---|---:|---:|---:|---:|---|
| Setup / baseline | — | — | — | — | See BASELINE-FAIL below |
| 1 Auth / perms / isolation | 18 | 10 | 1 | 7 | Auth API + login UI done; full role matrix / cross-tenant **BLOCKED** (no `QA_ADMIN_*`) |
| 2 Frontend panels | 42 vitest + login UI | 37 vitest + login error UI | 5 vitest | ~panel e2e | Full panel click-through **BLOCKED** without login |
| 3 Uploads | 28 | 22 | 1 | 5 | Live authenticated paths **BLOCKED**; unauth reject PASS |
| 4 Extraction | 15 | 12 | 2 | 1 | OCR **BLOCKED** (no tesseract); password PDF returns `None` |
| 5 Bifurcation | 12 | 4 | 6 | 2 | Junk guards FAIL; LLM path **BLOCKED** (Ollama 404) |
| 6 DB integrity | 8 | 3 | 1 | 4 | `serviceable_pincodes` missing; write/atomicity needs admin |
| 7 Validation | 40+ | 30 | 16 disagreements + 1 name | 0 | Cross-validator disagreements are bugs |
| 8 Tenants/CRUD | 10 | 0 | 0 | 10 | **BLOCKED** — no admin token |
| 9 WhatsApp E2E | 12 | 4 | 2 | 6 | Simulator works; tenant override FAIL; live WA not run |
| 10 Media | 12 | 6 | 2 | 4 | bare relative → `null`; live arrival **BLOCKED** |
| 11 RAG/FAQ/eval | 207 eval Qs | 142 | 65 | LLM mid-stop | Ollama ngrok 404; eval still ran embeddings/rules |
| 12 Orders/campaigns/… | 20 | 0 | 0 | 20 | **BLOCKED** — admin + payment sandbox |
| 13 Failure/security/ops | 14 | 8 | 3 | 3 | verify_token leak; DB path outside repo; Ollama down |

### BASELINE-FAIL (pre-existing — not new QA finds)

**Backend unittest:** `Ran 149 tests … FAILED (failures=4, errors=4)`

| ID | Test | Evidence |
|---|---|---|
| BASELINE-1 | `test_knowledge_gaps_and_async_uploads` | `ModuleNotFoundError: pytest` |
| BASELINE-2 | `test_category_tap_resolves_to_the_canonical_category` | `AttributeError: offerings_flow has no _unique_categories` |
| BASELINE-3/4 | `test_tenant_creation_records_actor_and_tenant`, `…rolls_back_if_audit_insert_fails` | `create_tenant() missing background_tasks` |
| BASELINE-5 | `test_admin_role_change_records_before_after…` | `AssertionError: 409 != 200` |
| BASELINE-6/7/8 | list-menu row-id tests (3 fails) | Duplicate `cat_general` row ids; case-variant categories → 2 sections |

**Frontend vitest:** `5 failed | 37 passed (42)` — uploads heading missing; IT “Coming next” pages missing text.  
**Frontend typecheck:** FAIL — `onboarding-kit-widget.tsx` / `onboarding-review-modal.tsx` (`variant` vs `tone`, unused imports).  
**Smoke:** `scripts/smoke_gating.py` FAIL (tenant resolve → always `leeway-softech`); `scripts/smoke_menu.py` FAIL (TrooGood greeting = Leeway).  
**Startup:** FAQ FAISS build ERROR (`inhomogeneous shape (475,)`); server still came up. Tesseract missing warning.  
**Eval (this run, all datasets resolved as tenant `leewaysoftech`):** leeway 55/58 **94.8%**; banking 20/46 **43.5%**; finance 31/45 **68.9%**; travel 36/58 **62.1%**.

---

## 2. Bug table (severity sorted)

| ID | Severity | Area & Section | Steps + exact input | Expected | Actual (evidence) | Suspected file:line | Repro? |
|---|---|---|---|---|---|---|---|
| BUG-01 | **Blocker** | Tenant routing / S9+S8 smoke | `POST /api/test-simulator` body `tenant_id=empty-test` then `troogood`, message `hi`, user_type `b2c` (twice) | Menu/header for requested tenant | Always `header: Leeway Softech` — `reports/qa/simulator_*.json`; `get_active_test_tenant()=='leeway-softech'` | `orchestrator.py:162` (`resolve_effective_tenant_id` default `allow_test_override=True`); `resolver.py:99-107` | Yes ×2 |
| BUG-02 | **Blocker** | Active test override / S9 | Any simulator call while console “active test tenant” = leeway | Explicit `tenant_id` must win in simulator | Override logs “ignoring hint”; smoke_gating/menu fail same way | `shared/tenancy/resolver.py:93-107` | Yes |
| BUG-03 | **Major** | Phone validators / S7 | Input `9876543210` (and `919…`, `098…`, formatted variants) through all validators | Same accept + normalise to `+919876543210` | `validate_mobile`/`is_valid_phone_input` accept; `_require_phone`/`extract_first_valid_phone` **reject** (need `+91…`). 16 disagreements in `reports/qa/section7_disagreements.json` | `shared_validators.py:41-57` vs `schemas.py:165-199` | Yes |
| BUG-04 | **Major** | Phone / S7 | Profile/onboarding phone `9876543210` | Accept Indian 10-digit like checkout | Profile `_require_phone` ValueError requiring country code | `schemas.py:186-198` | Yes |
| BUG-05 | **Major** | Bifurcation junk / S5 | Names: `Terms & Conditions`, `Page 3 of 3`, `FAQ`, `Disclaimer` | `is_junk_offering_name` → True | All False — `section5_junk_guards` FAIL | `bifurcation_guards.py:60-128` | Yes |
| BUG-06 | **Major** | Security / S13+S1 | `GET /webhook/status` unauthenticated | No secrets | Returns plaintext `verify_token` (len 25) — `section1_auth_evidence.jsonl` | `routes/status.py:38-48` | Yes ×2 |
| BUG-07 | **Major** | Ops config / S13 | Boot this checkout | DB under project | `DB_PATH=C:\Users\Leeway\Desktop\chatbot2\faq.db` outside repo (`section13_db_path.json`); local `faq.db` empty/misleading | `routing/config.py:58-61` + env `ROUTING_DB_PATH` | Yes |
| BUG-08 | **Major** | FAQ index startup / Setup | Start `backend/main.py` | FAQ index builds | `FAQ index init FAILED: inhomogeneous shape (475,)` — server log | `faq/service.py:681` | Yes |
| BUG-09 | **Major** | List menus / baseline S9 | Duplicate/case-variant categories | Unique WhatsApp list row ids | Duplicate `cat_general` reaches API — baseline tests | `test_list_menu_row_ids.py` + offerings menu builders | Yes (unit) |
| BUG-10 | **Major** | Media URL / S10 | `resolve_public_media_url("uploaded_files/kb/x.jpg")` or bare `x.jpg` | Public URL or explicit failure | Returns `null` silently — `section10_media.json` | `kb/services/whatsapp.py:849-928` | Yes |
| BUG-11 | **Major** | Extraction / S4 | Upload/process `password_protected.pdf` | Structured error to UI/status | `process_file` → `None` after exception (logged only) | `extract.py:202-373` | Yes ×2 |
| BUG-12 | **Major** | Health/send2 / S13 | `GET /webhook/health` | Clear credential check | `send2_api.ok=false`, body “Please provide Username” while `/webhook/status` says username_set true | `routes/status.py:60+` vs credential field names in payload | Yes |
| BUG-13 | **Minor** | Name sanitize / S7 | Name=`<script>alert(1)</script>` | Reject or strip to empty/invalid | Accepted as valid name `lt;scriptgt;alert(1)…` | `shared_validators.py:13-38` | Yes |
| BUG-14 | **Minor** | Frontend / S2 | Navigate uploads / IT info routes (vitest) | “Uploads” heading; “Coming next” | Missing — 5 vitest fails | `views.test.tsx` + panels/router | Yes |
| BUG-15 | **Minor** | Typecheck / S2 | `npm run typecheck` | Clean | Badge `variant` vs `tone`; unused imports in onboarding components | `onboarding-kit-widget.tsx:151+`, `onboarding-review-modal.tsx` | Yes |
| BUG-16 | **Minor** | Serviceability / S6+S7 | `check_serviceability("380001")` | DB table or clean fallback | Log: `no such table: serviceable_pincodes` then prefix fallback | `shared_validators.py:69-88` + missing migration | Yes |
| BUG-17 | **Minor** | Tables extract / S4 | `clean_multi_page.pdf` pipe table | Tables extracted | `tables_len: 0` (text OK) | `extract.py` table extractor | Yes |
| BUG-18 | **Minor** | Frontend limits / S3 | Compare FE/BE upload caps | FE==BE | Admin 20MB OK; `tenant_files.MAX_UPLOAD_BYTES` is `null` in module | `tenant_files.py` vs `admin.py:32` | Yes |
| BUG-19 | **Blocker** (env) | Ollama / S5+S11+S13 | Hit configured `OLLAMA_BASE_URL/.../api/tags` | Reachable `qwen3:8b` | HTTP 404 on ngrok host; localhost:11434 down | env / ops | Yes |
| BUG-20 | **Major** (env) | OCR / S4 | `scanned_ocr.pdf` | OCR text or graceful UI error | Tesseract exe missing; OCR skipped — empty OCR pages | `extract.py` + missing `TESSERACT_CMD` | Yes |

---

## 3. Coverage checklist

| Section | Status | Evidence types |
|---|---|---|
| Setup & baseline | **Done** | Server log, unittest/vitest/typecheck outputs under `reports/qa/` |
| 1 Auth | **Partial** | HTTP status/body JSONL; browser login screenshot/text; rate-limit 429 |
| 2 Frontend panels | **Partial** | Vitest; browser login only — rest **BLOCKED** (no credentials) |
| 3 Uploads | **Partial** | Local process_file matrix; unauth HTTP probes; limits JSON |
| 4 Extraction | **Partial** | `section4_extract.json`; tesseract BLOCKED |
| 5 Bifurcation | **Partial** | Junk/heuristic unit evidence; LLM/auto-publish BLOCKED |
| 6 DB | **Partial** | sqlite inspect on real DB; missing table; write suites BLOCKED |
| 7 Validation | **Done** | Matrices JSON + disagreements file |
| 8 Tenants CRUD | **BLOCKED** | Need `QA_ADMIN_USER`/`QA_ADMIN_PASS` |
| 9 WhatsApp E2E | **Partial** | Simulator capture; tenant override FAIL; live send2 to test number not run |
| 10 Media | **Partial** | resolve_public_media_url matrix; live WA arrival BLOCKED |
| 11 RAG/eval | **Partial** | eval accuracies; Ollama chat BLOCKED |
| 12 Orders/payments/… | **BLOCKED** | Admin + sandboxes |
| 13 Security/ops | **Partial** | health/status/CORS/webhook/db-path tests |

---

## 4. Validation disagreement table (Section 7)

| Input | validate_mobile | is_valid_phone_input | bifurcation `_normalize_phone` | extract_first_valid_phone | `_require_phone` |
|---|---|---|---|---|---|
| `9876543210` | ✅ → `+919876543210` | ✅ | keeps `9876543210` | ❌ empty | ❌ needs `+91…` |
| `919876543210` | ✅ | ✅ | keeps raw | ❌ | ❌ |
| `09876543210` | ✅ | ✅ | keeps raw | ❌ | ❌ |
| `+919876543210` | ✅ | ✅ | keeps | ✅ (as given) | ✅ |
| `+91 98765 43210` | ✅ | ✅ | keeps spaced | ✅ | ✅ |
| `5876543210` | ❌ | ✅ (**disagree**) | nonempty | ❌ | ❌ |
| `1234567890` | ❌ | ✅ (**disagree**) | nonempty | ❌ | ❌ |
| `+1 202 555 0123` | ❌ | ✅/country (**disagree** vs Indian checkout) | nonempty | may extract | may accept intl |

Full dump: `reports/qa/section7_disagreements.json` (16 rows).

---

## 5. Media delivery matrix (Section 10)

| Media type × trigger | Flag / condition | Arrived? | Evidence |
|---|---|---|---|
| Public HTTPS URL resolve | any | resolve OK | `section10_media.json` |
| `/uploaded_files/...` + PUBLIC_BASE set | — | URL rewritten to cloudflare base (may be stale tunnel) | same |
| bare `uploaded_files/...` or `x.jpg` | — | **`null` silent** | BUG-10 |
| `send_sticker` | — | returns `False` (disabled) | PASS intentional |
| Product/catalogue/brochure live WA | brochure flag on/off | **BLOCKED** | no live test number run this pass |
| Capture-only begin | — | ON | `whatsapp_sender.begin_capture` |

---

## 6. Upload matrix (Section 3) — path × type × size

| Path | Types tried | Size extremes | Result |
|---|---|---|---|
| Local `process_file` (shared by ingest) | pdf/docx/txt/md/csv/xlsx/UPPER.PDF/spaces | 0-byte pdf, corrupt, password, lie-ext | Supported types OK; unsupported → None; password → **None/FAIL**; 0-byte opens fail logged |
| Unauth `POST` admin/tenant/offerings/brochure/image | tiny pdf | — | No `200` (fail-closed) PASS |
| Authenticated admin/tenant/KB/batch/bifurcate/offerings/intake/kits/brochure/logo/chat | — | 0 / 20MB±1 | **BLOCKED** (no admin token) |
| FE vs BE limits | — | 20MB | FE `MAX_UPLOAD_BYTES=20MiB` matches admin; tenant_files constant missing |

Test pack: `qa_testdata/` (32 files + generator).

---

## 7. Silent failure list (highest value)

1. **Simulator/orchestrator ignores explicit `tenant_id`** when `active_test_tenant` is set — looks “successful” with wrong tenant’s menu (`BUG-01/02`).  
2. **`resolve_public_media_url` returns `null`** for relative/bare paths — callers can treat as soft-skip; media never sent (`BUG-10`).  
3. **Password-protected PDF → `process_file` returns `None`** with only logs — upload UI can sit in processing/error without structured `error_message` (`BUG-11`).  
4. **Scanned PDF OCR skipped** when tesseract missing — empty page text, easy to look like “extracted OK” with no content (`BUG-20`).  
5. **Junk headings can become offerings** — guards don’t flag Terms/FAQ/Page N (`BUG-05`).  
6. **`/webhook/health` vs credential flags disagree** — status says username set, health says “Please provide Username” (`BUG-12`).  
7. **FAQ index build fails at startup** but process continues — FAQ RAG may be empty while KB index OK (`BUG-08`).  
8. **HTML name input accepted** after broken escape/strip (`BUG-13`).

---

## 8. Env / restore notes

| Item | State |
|---|---|
| `SEND2_*`, `OLLAMA_*`, `PUBLIC_BASE_URL` | All SET in `routing/.env` |
| Ollama | Unreachable (ngrok 404; no local 11434) |
| Tesseract | Missing |
| Admin login for write tests | **Not available** — set `QA_ADMIN_USER` / `QA_ADMIN_PASS` to unblock S2 panels, S3 live uploads, S8, S12 |
| DB backup | Real DB: `reports/qa/faq.db.REAL-backup-20261029-103317`; earlier backup of empty local `faq.db` is **not** the live DB |
| Mutations this pass | Simulator reset for `qa-throwaway-001` only; no tenant hard-delete; no live WhatsApp send |
| Could not restore | N/A (no destructive tenant writes). Leave `active_test_tenant=leeway-softech` as found |

---

## Follow-up: ngrok console session (2026-10-29)

- Frontend URL `https://prominent-faster-dropper.ngrok-free.dev/` — login as provided superadmin **succeeded** (tenant list: MakeMyTrip Active Test Bot, Prestigue, sbi).
- Same credentials against local `http://127.0.0.1:9000/api/auth/login` → **Invalid credentials** (ngrok app is a different backend/DB than the local QA server).
- **BUG-21 (Major, S5/S8 live):** MakeMyTrip Profile `Display name` and `Company name` are both truncated booking-checklist text: `Booking Checklist Confirm destination, dates, traveller names as per passport, r` — also used as WhatsApp menu header. Suspected brand overwrite from bifurcation/PDF intake. Evidence: browser Profile + Menu panels.
- Panels loaded OK via deep-link: Overview, Uploads, Profile, Menu, Packages (6), Team. Uploads Option B default kit showed Real Estate for a Tours tenant (wrong-vertical kit default — Minor).

## Setup evidence (brief)

- Server: started with FAQ index error then `Uvicorn running on http://0.0.0.0:9000`.  
- Login API: empty/wrong/SQLi → 401 generic `Invalid credentials`; rate limit → **429** after rapid fails; second `first-admin` → 403.  
- Frontend login: wrong creds → UI **“Invalid credentials”** (browser). No show/hide password control.  
- Health paths: `/health` root **404**; real endpoints `/webhook/health`, `/webhook/status`.
