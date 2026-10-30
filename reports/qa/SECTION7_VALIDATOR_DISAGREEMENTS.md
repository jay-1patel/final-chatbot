# Section 7 — Phone Validation Disagreements Analysis

## Headline Finding
**`shared_validators.py` is dead code in production.** It's imported only by `test_qa_section7_phone.py`. Every live path uses `shared/tenancy/schemas.py` instead. They genuinely disagree on ~50% of inputs.

## Validator Agreement Matrix (Real Inputs → Real Outputs)

| Input | validate_mobile (checkout test) | is_valid_phone_input (conversations) | _normalize_phone (bifurcator) | extract_first_valid_phone / _require_phone (profile) |
|---|---|---|---|---|
| `9876543210` | valid → `+919876543210` | True | returns raw `'9876543210'` | **ValueError**: "must be country code + 10 digits" |
| `+919876543210`, `+91 98765 43210` | valid | True | raw | accepts | accepts |
| `5876543210`, `1234543210` (landline start) | **invalid** (requires 6-9) | **True** (10 digits = fine) | returns raw | reject | reject |
| `98765432109` (11-digit) | invalid | invalid | **returns raw** (≥10 rule) | reject | reject |
| `9876543210x123`, `🇮🇳9876543210` | invalid | invalid | **returns raw** — strips non-digits, counts ≥10 | reject | reject |
| `+1 202 555 0123` (US number) | **invalid** (India-only) | **True** (country '1' accepted) | raw | **accepts** | **accepts** |
| `''` / `'   '` | invalid | invalid | `''` | passes through unvalidated ("not set") | passes through |

## Root Causes of Disagreement

### 1. Leading-digit rule conflict
`validate_mobile` requires `^[6-9]\d{9}$` (Indian mobile); `is_valid_phone_input` accepts any 10 digits. So landlines like `1234567890` pass conversation flows but fail checkout.

**File impacts:**
- `flow_runner.py:169-172` — uses permissive `is_valid_phone_input` for user chat input
- `shared_validators.py:41-57` — strict `validate_mobile` used by... only tests. Production checkout probably uses `is_valid_phone_input`.

### 2. Country-code requirement split
`_phone_ok` (`schemas.py:139-146`) requires `+` + table country code + exactly 10 digits. Bare digits rejected by profile paths but accepted by both user-input paths.

### 3. `_normalize_phone` is not a validator
`bifurcation_extract.py:304-310`: strips non-digits (keeps `+`), needs ≥10 digits, returns original messy string. Accepts emoji-prefixed, alpha-suffixed, and 11-digit junk.

### 4. Internal pipeline conflict (data extraction → publish rejection)
Extract regex at `bifurcation_extract.py:435-443` matches bare `9876543210` (first alternative has `+91` optional) and writes to `brand["support_phone"]`. On publish, `BrandProfile._check_support_phone` (`schemas.py:362-365`) calls `_require_phone` which raises `ValueError` — extraction produces values the profile rejects. Same at `pdf_intake.py:1006`.

## Name Sanitization — XSS Bug

**Root cause:** `html.escape` runs BEFORE character-class strip (`shared_validators.py:15`). 
- `<script>alert(1)</script>` → escapes to `&amp;lt;script&amp;gt;alert(1)&amp;lt;/script&amp;gt;` → strip removes `&amp;` but leaves `lt;scriptgt;alert(1)lt;/scriptgt;` → 36 chars, has `[a-zA-Z]` match → `valid: True`.

**Where it should be used but isn't:**
- `flow_runner.validate_answer` rule `"name:<min>"` (`flow_runner.py:173-177`) — length check only, no HTML sanitization
- Raw HTML flows into `_save_lead` stored in `leads.name` and bot replies
- `sanitize_address` (`shared_validators.py:21-25`) has the same escape-before-strip flaw

**Affected fields:** name, address, anywhere collected from user input.

## Serviceability Fallback

- Table `serviceable_pincodes` missing from DB (DB has 70 tables, none pincode-related). Migration exists at `run_b2c_migration.py:137-148` but never run.
- Falls back to hardcoded Gujarat prefixes 360–396 (env var not set).
- Consequence: delivery eligibility decided by coarse 3-digit prefix match. Admin overrides via `is_active=0` unreachable. Failure invisible except WARNING per call.

## All Validator Functions Summary

1. `validate_mobile(raw)` — India mobile only, strict 6-9 lead digit. Dead code outside tests.
2. `validate_name(raw)` — Escape-before-strip XSS bug. Only called by QA test.
3. `validate_pincode(raw)` — `^[1-9][0-9]{5}$`. Correct but no caller.
4. `validate_address(raw)` — sanitize + length 10-250. Same escape-before-strip bug.
5. `validate_qty(raw, moq, max_qty, stock)` — int conversion, bounds checks. Test cases all pass.
6. `check_serviceability(pincode)` — DB query fails silently, falls back to prefix whitelist.
7. `_normalize_phone(raw)` — Returns raw string, not a validator. Used by bifurcator extract.
8. `_phone_ok()` / `extract_first_valid_phone()` / `_require_phone()` — Strict format required, ~200 country codes. Used by profile/schema routes.
9. `is_valid_phone()` — Boolean version of _phone_ok. Used by distributors.py, pdf_intake.py.
10. `is_valid_phone_input()` — Permissive. Used by flow_runner, callbacks, distributor order flow.

Evidence JSON saved to: `reports/qa/section7_disagreements.json`
