# Bugs & Solution Options — final-chatbot QA

**Sources:** local baseline + ngrok live (`prominent-faster-dropper.ngrok-free.dev`)  
**Date:** 2026-10-29  
**Legend:** **A** = recommended / fix-in-code · **B** = config/ops · **C** = data cleanup · **D** = accept / document

---

## Priority order (what to do first)

1. Fix Active Test Tenant override ignoring explicit `tenant_id` (Blocker — breaks multi-tenant WhatsApp/simulator)
2. Stop bifurcation from overwriting brand with junk / checklist text
3. Unify phone validators
4. Remove webhook `verify_token` leak
5. Fix FAQ FAISS build + list-menu duplicate row ids
6. Data cleanup on live tenants (MakeMyTrip brand, Prestigue intents, `[Confirm]` placeholders)
7. Frontend / typecheck / badge / route minors

---

## BLOCKERS

### B1 — Active Test Tenant overrides every tenant (simulator + live bot path)
**IDs:** BUG-01, BUG-02, NGROK-01  
**Symptom:** `POST /api/test-simulator` with `tenant_id=p|troogood|s|makemytrip` all return MakeMyTrip welcome. Console menu preview for Prestigue is correct; WhatsApp/simulator is wrong.  
**Cause:** `resolve_effective_tenant_id()` applies `active_test_tenant` first and **ignores** explicit hint (`resolver.py`). Orchestrator calls it with `allow_test_override=True` by default (`orchestrator.py` ~162).  
**Suspected:** `shared/tenancy/resolver.py:80-107`, `backend/services/orchestrator.py:162`, `routes/test_simulator.py`

| Option | Solution | Pros | Cons |
|---|---|---|---|
| **A (recommended)** | When caller passes explicit `tenant_id` (simulator, admin test, `#tenant` already set), **prefer hint over** `active_test_tenant`. Keep override only for unbound live WhatsApp traffic. | Fixes multi-tenant testing; matches user expectation | Small behaviour change for “single-number testing” |
| **B** | Simulator always calls `resolve_effective_tenant_id(..., allow_test_override=False)` when body has `tenant_id` | Quick, localised | Live webhook path may still be wrong if override on |
| **C** | Ops: clear Active Test Bot before every multi-tenant test | No code | Easy to forget; still dangerous in prod |
| **D** | Document “Active Test Bot always wins” | Zero code | Leaves product broken for multi-tenant QA |

**Also do (data):** Turn off / clear Active Test Bot on ngrok until A/B ships.

---

## MAJORS — Product / data

### M1 — MakeMyTrip brand overwritten with checklist text
**IDs:** BUG-21, NGROK-02  
**Symptom:** Display name & Company name = `Booking Checklist Confirm destination, dates…` (also WhatsApp menu header).  
**Cause:** Bifurcation / PDF intake wrote a policy/FAQ line into `brand.name` without brand-placeholder protection.

| Option | Solution |
|---|---|
| **A** | Harden `is_placeholder_brand_value` + reject names that look like sentences / start with “Booking Checklist”, “Terms”, “FAQ”, length > N without company cues; never overwrite non-empty brand with longer paragraph-like text |
| **B** | Require human approve for brand fields on publish (staged brand) |
| **C (now)** | Manually edit MakeMyTrip Profile → set Display/Company back to “MakeMyTrip” → Publish |
| **D** | Re-run kit upload with brand locked |

---

### M2 — Prestigue intents contaminated with another kit (Skyline / Ahmedabad)
**IDs:** NGROK-03  
**Symptom:** Intents mention Skyline Realty, SG Highway, Ahmedabad RERA while offerings are Bangalore Prestige.

| Option | Solution |
|---|---|
| **A** | On bifurcate/apply: vertical + brand lock; drop intents whose entities don’t match tenant brand/geo; dedupe against existing |
| **B** | `auto_publish=false` always for intents; review UI must approve |
| **C (now)** | Delete/edit bad intents in Intents Editor → Publish |
| **D** | Hard reset draft from clean kit |

---

### M3 — Live offerings contain `[Confirm: …]` placeholders
**IDs:** NGROK-04  

| Option | Solution |
|---|---|
| **A** | Bifurcation guard: reject offering names/descriptions matching `\[Confirm` / `TODO` / `TBD` |
| **B** | Publish validator fails if placeholders present |
| **C (now)** | Edit Prestigue properties; remove bracket notes; Publish |

---

### M4 — Phone validators disagree across checkout vs profile
**IDs:** BUG-03, BUG-04  
**Symptom:** `9876543210` OK in `validate_mobile`; rejected by `_require_phone` (needs `+91…`). `5876543210` rejected by checkout but accepted by `is_valid_phone_input`.

| Option | Solution |
|---|---|
| **A (recommended)** | Single shared normaliser: strip to digits → Indian mobile rules (6–9…) → always store E.164 `+91XXXXXXXXXX`. Profile `_require_phone` should accept bare 10-digit and normalise |
| **B** | Change UI to only accept `+91` and show format hint (no backend unify) |
| **C** | Keep both but document “checkout = India mobile, profile = E.164 only” | Confusing UX |

**Files:** `backend/services/shared_validators.py`, `shared/tenancy/schemas.py`, `bifurcation_extract._normalize_phone`

---

### M5 — Junk headings can become offerings
**IDs:** BUG-05  
**Symptom:** `is_junk_offering_name("Terms & Conditions")` → False.

| Option | Solution |
|---|---|
| **A** | Expand `_JUNK_NAMES` / regex: Terms, Conditions, FAQ, Page \d, Disclaimer, Table of Contents, Price List Notes, etc. |
| **B** | LLM-only filter with heuristic fallback list |
| **C** | Manual review staged offerings only |

---

### M6 — Webhook status leaks verify_token
**IDs:** BUG-06  

| Option | Solution |
|---|---|
| **A (recommended)** | Remove `verify_token` from public `/webhook/status` or require auth; return `verify_token_set: bool` only |
| **B** | Move status under `/api/admin/...` |
| **D** | Leave as-is for debugging | **Security risk** |

**File:** `backend/routes/status.py:38-48`

---

### M7 — FAQ FAISS index fails at startup
**IDs:** BUG-08  
**Symptom:** `np.array(all_embeddings)` inhomogeneous shape (475,).

| Option | Solution |
|---|---|
| **A** | Filter/pad embeddings to fixed dim; skip corrupt rows; log FAQ ids that fail |
| **B** | Rebuild FAQ embeddings table / clear bad `cached_embeddings` |
| **C** | Fail closed: mark FAQ retrieval disabled in `/health` |

**File:** `backend/faq/service.py:681`

---

### M8 — Duplicate WhatsApp list row ids
**IDs:** BUG-09, BASELINE menu tests  

| Option | Solution |
|---|---|
| **A** | Before send: uniquify row ids (`cat_general`, `cat_general__2`); collapse case-variant categories |
| **B** | Fix category slug generator only |
| **C** | Update tests to match current behaviour | Leaves Meta API risk |

---

### M9 — Media URL silent null for relative paths
**IDs:** BUG-10  

| Option | Solution |
|---|---|
| **A** | Normalise bare/`uploaded_files/...` → `/uploaded_files/...` then PUBLIC_BASE / imghippo; if still null, log ERROR + user-visible “media unavailable” |
| **B** | Force all uploads to absolute public URLs at store time |
| **C** | Disable media send when resolve fails (already partly true) but surface in admin |

**File:** `kb/services/whatsapp.py:849-928`

---

### M10 — Password PDF → `process_file` returns None
**IDs:** BUG-11  

| Option | Solution |
|---|---|
| **A** | Catch encrypted PDF; return `{error: "password_protected", status: "error"}` so UI/`error_message` populate |
| **B** | Reject at upload with HTTP 400 before process |
| **C** | Document “password PDFs unsupported” |

---

### M11 — send2 health vs status disagree
**IDs:** BUG-12  
**Symptom:** status says username set; health gets “Please provide Username”.

| Option | Solution |
|---|---|
| **A** | Align health check payload field names with real send2 API (`user_name` vs `username`) |
| **B** | Health check only “credentials non-empty” without calling send2 |
| **C** | Fix SEND2_* env mapping |

---

### M12 — DB path points outside this repo (local QA env)
**IDs:** BUG-07  

| Option | Solution |
|---|---|
| **A/B** | Set `ROUTING_DB_PATH` to this project’s `faq.db` (or document that ngrok uses its own DB) |
| **C** | Symlink / copy — avoid dual DBs |
| **D** | Always test only via ngrok (your current preference) |

---

## MINORS

| ID | Bug | Solution options |
|---|---|---|
| NGROK-05 | Callbacks badge **5** vs list **0** | **A** Fix badge query to match list filters/tenant scope · **B** Hide badge when 0 after load · **C** Ignore |
| NGROK-06 | `#/tenants/:id/integrations` → Unknown view | **A** Register route id to match nav (`integrations` / google-connect panel) · **B** Remove nav item until built |
| NGROK-07 | Sidebar tenant chip stale after deep-link | **A** Sync selected tenant from route param on every navigation · **B** Force full remount on tenant change |
| BUG-13 | HTML name accepted after broken sanitize | **A** Reject if no letters after strip; don’t `html.escape` then strip tags leaving `lt;script…` · **B** Allowlist charset |
| BUG-14 | Vitest: Uploads heading / Coming next | **A** Align copy with tests or update tests · **B** Implement missing panels |
| BUG-15 | Typecheck: Badge `variant` vs `tone` | **A** Change to `tone=` · **B** Add `variant` alias on Badge |
| BUG-16 | Missing `serviceable_pincodes` table | **A** Add migration/create in `init_db` · **B** Rely on prefix fallback only (document) |
| BUG-17 | Pipe tables not extracted as tables | **A** Detect `|` markdown/pipe tables in extract · **B** Accept text-only |
| BUG-18 | `tenant_files.MAX_UPLOAD_BYTES` unset | **A** Share constant with admin 20MB · **B** Document single upload entrypoint |
| BUG-19 | Ollama URL 404 | **B** Fix `OLLAMA_BASE_URL` / run local Ollama with `qwen3:8b` |
| BUG-20 | Tesseract missing | **B** Install tesseract + set `TESSERACT_CMD` · **A** Surface OCR-unavailable in upload status |

---

## BASELINE test debt (fix suite vs product)

| ID | Issue | Solution options |
|---|---|---|
| BASELINE-1 | `pytest` missing for knowledge-gaps test | **A** Add pytest to requirements · **B** Rewrite as unittest |
| BASELINE-2 | `_unique_categories` missing | **A** Restore helper · **B** Update test to new API |
| BASELINE-3/4 | `create_tenant` needs `background_tasks` | **A** Update tests with mock BackgroundTasks · **B** Make arg optional |
| BASELINE-5 | Admin role change 409 | **A** Fix conflict logic · **B** Fix test fixtures |

---

## Suggested sprint plan

| Sprint | Items | Outcome |
|---|---|---|
| **S0 (today, ops)** | Clear Active Test Bot; manually fix MakeMyTrip brand; scrub Prestigue intents/`[Confirm]` text | Live WhatsApp stops lying about tenant |
| **S1** | B1 routing fix + M6 verify_token + M4 phone unify | Multi-tenant safe; security + forms |
| **S2** | M5 junk guards + M1 brand protection + M10 upload errors | Bifurcation quality |
| **S3** | M7 FAISS + M8 row ids + M9 media URLs | Reliability |
| **S4** | Frontend minors + typecheck + badge/route | Console polish |

---

## What we recommend you choose

| Bug | Pick |
|---|---|
| Active Test override | **A** — explicit `tenant_id` wins |
| Brand corruption | **A** + **C** (code + immediate data fix) |
| Phone validators | **A** — one normaliser |
| verify_token leak | **A** — redact |
| Junk offerings | **A** — expand guards |
| Live dirty data | **C** — clean MakeMyTrip + Prestigue now |
| Ollama / Tesseract | **B** — env/install |
| DB dual-path | **D** if ngrok-only, else **B** point env at one DB |
