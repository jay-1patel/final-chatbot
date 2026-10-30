# QA Baseline Report — Initial Assessment

## Environment
- Server: Running on port 9000 (PID 15544)
- Database: External path `C:\Users\Leeway\Desktop\chatbot2\faq.db`
- Ollama: Via ngrok tunnel (`prominent-faster-dropper.ngrok-free.dev`)
- Tesseract: **Not installed** — OCR blocked
- SQLAlchemy: **Missing from requirements.txt** but referenced in `backend/db/*.py` (would crash on import if not pre-installed elsewhere)

## Test Suite Baseline (All existing backend/test_*.py + scripts/test_*.py)

| Result | Count |
|---|---|
| PASSED | 165 |
| FAILED | 32 |
| TOTAL | ~197 |

### Failed Tests by Category

#### Section 1 — Auth (existing tests)
- All 8 PASS ✓

#### Section 3 — Upload Matrix
- **FAILED**: `test_file_type_local_processing_matrix` — local processing logic differs between expected and actual

#### Section 4 — PDF Extraction
- **FAILED**: `test_extraction_pack` — FAQ extraction incomplete for multi-page PDF (has_brand, has_phone, has_email, has_price True, but has_faq=False)

#### Section 5 — Bifurcation Guards
- **FAILED**: `test_junk_offering_guards` — wrong function signature in test vs code
- **FAILED**: `test_placeholder_brand_protection_unit` — same issue (`is_placeholder_brand_value` needs 2 args, test passes 1)

#### Section 7 — Phone/Form Validation
- **FAILED**: `test_mobile_matrix_and_disagreements` — validator disagreement found
- **FAILED**: `test_name_pincode_address_qty` — XSS bypass: `<script>alert(1)</script>` accepted as valid name

#### Tenant Approvals (ALL 8 FAIL)
- `test_admin_cannot_create_tenants_or_publish_directly`
- `test_profile_rejects_invalid_contact_details`
- `test_publish_is_tenant_scoped_and_applies_submitted_snapshot`
- `test_publish_rejection_keeps_live_version`
- `test_publish_submission_requires_tenant_and_draft`
- `test_registration_approval_conflict_when_tenant_appeared`
- `test_registration_rejection_creates_nothing`
- `test_registration_rejects_invalid_contact_details`
- `test_registration_submission_and_approval`
- `test_superadmin_registers_company_admin_completes_for_approval`

#### Audit / Tenant Audit
- `test_admin_role_change_records_before_after_and_changed_fields`
- `test_tenant_creation_records_actor_and_tenant`
- `test_tenant_creation_rolls_back_if_audit_insert_fails`

#### List Menu Row IDs (4 fails)
- `test_case_variant_categories_form_one_section`
- `test_category_selector_never_repeats_a_row_id`
- `test_category_tap_resolves_to_the_canonical_category`
- `test_duplicate_row_ids_are_made_unique_before_sending`

#### WhatsApp Routing Dedup (6 fails)
- `test_listener_processes_each_polled_message_id_once`
- `test_message_without_active_tenant_stops_before_classification`
- `test_orchestrator_capture_only_prevents_listener_double_send`
- `test_tenant_resolution_exception_stops_message_processing`
- `test_webhook_drops_message_when_phone_has_no_active_tenant`

#### Scripts
- `test_bifurcation` (TypeError: save_p...)
- `test_dlf_bot` (async function issue)
- `test_3_real_estate_docx_bifurcation`
- `test_5_publishing_and_verification`

### Critical Findings Already

1. **SQLAlchemy missing from requirements.txt** — would fail on fresh install
2. **Tesseract not installed** — all OCR tests blocked
3. **`/health` endpoint returns 404** — spec expects `/status`, `/health`
4. **`/logs` and Prometheus metrics** endpoints may not exist
5. **XSS bypass** in name validation
6. **Placeholder brand value function** has wrong signature in existing tests
7. **Tenant approvals system** — ALL 8 tests fail (systemic issue?)
8. **Serviceable pincodes table** missing — serviceability checks silently fall back
9. **Webhook status leaks verify_token** without auth (detected in section1 test line 129)
10. **FAQ extraction incomplete** for multi-page PDFs

## Notes
- Server is running but many "live" tests use mocks/local DB operations
- pytest-mock not reliably available (tests sometimes skip/mock issues)
- Some tests require live server access at http://127.0.0.1:9000
