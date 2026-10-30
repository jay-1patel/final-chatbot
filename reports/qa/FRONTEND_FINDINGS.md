# Frontend Button Coverage Analysis — QA Section 2

## Findings (by severity)

### CRITICAL / HIGH (Silent wrong behavior, data loss risk)

**F-01: Stale edit form on switching edit target — SILENT WRONG RECORD OVERWRITE**
- File: `frontend/src/components/tenants/campaigns-panel.tsx:388-403` + `:1152`
- Bug: `CampaignForm` initializes with `useState(() => toShape(initial))` — no `key` prop.
- Clicking "Edit" on campaign B while editing campaign A silently submits through `editing.id = B` but the form still has campaign A's data.
- Fix needed: add `key={editing?.id}` to `<CampaignForm>`.

**F-02: Silent action failures — error never rendered**
- File: `frontend/src/components/tenants/intents-editor.tsx:34-80`
- Bug: `useAction`'s `action.error` is never displayed in this panel. When Save draft / Save & publish / delete fails, spinner stops with zero feedback.
- Other panels (Campaigns/Templates/Segments) DO render `action.error`; Intents does not.

**F-03: Duplicate intent creation — rename allows creating second intent**
- File: `frontend/src/components/tenants/intents-editor.tsx:122`
- Bug: Name input `disabled` condition can never be true because form only renders inside `editing && draft`. Editing existing intent → changing name → saveIntent creates a duplicate intent (intents are name-keyed).
- Also: no `draft.name.trim()` guard — empty name can be POSTed.

**F-04: Blank page for known-but-unrouted view**
- File: `frontend/src/App.tsx:198` + `frontend/src/lib/navigation.ts:188`
- Bug: `'flows'` listed in KNOWN_VIEWS but no branch renders a panel. Unknown views show blank instead of alert.
- Root cause of truth `knownViews()` is exported but used nowhere — manual `KNOWN_VIEWS` list has drifted from nav definition.

**F-06: No error boundary anywhere in app**
- Any throw inside any panel (e.g., `gap.confidence_score.toFixed(2)` at `uploads-panel.tsx:788` if null) white-screens entire console with no recovery.

### MEDIUM (User experience issues, minor data risk)

**F-05: Wrong count badge on Callbacks nav item**
- File: `navigation.ts:163` + `app-shell.tsx:263`
- Bug: `callbacks` marked `showsCount: true` but `contentCount` shows product count for EVERY items with `showsCount: true`.

**F-07: Per-keystroke API requests, no debounce**
- Files: `orders-panel.tsx:39-43`, `uploads-panel.tsx:85-88`
- Bug: `search` in `useAsync` deps; every character fires backend request, table flickers per keystroke.

**F-08: Polling false-ready on same-named re-upload**
- File: `frontend/src/lib/uploads.ts:289-312`
- Bug: `waitForUploadReady` matches by filename. Older ready file with same name makes poll return immediately while new upload still processing → "Published live" toast for unfinished work.

**F-09: `useAction.run` has no re-entrancy guard**
- File: `frontend/src/lib/hooks.ts:60-74`
- Bug: Sets `busy` but doesn't block concurrent calls. Callers without `loading={busy}`: "Send test" (`campaigns-panel.tsx:1536-1542`), template Approve/Reject (`:639-652`) — rapid clicks double-fire POSTs.

**F-10: Login has no show/hide password control**
- File: `login-view.tsx:55-63`
- Spec says: test show/hide password if present. It ISN'T present — plain `type="password"` Input with no toggle.

### LOW

**F-11: Upload-path validation inconsistency**
- File: `attachments.ts:32-43`
- Bug: Size-only check; renaming `virus.exe` to `x.pdf` bypasses picker accept list; empty files pass.

**F-12: Tenant-switcher dropdown never closes on outside click**
- File: `app-shell.tsx:141-199`
- Bug: `switcherOpen` only resets via option buttons or route-change effect; no outside-pointerdown handler.

## Test Coverage Gap

| Panel | Tested Buttons | Untested Controls |
|---|---|---|
| Login | submit success/failure | show/hide password, Enter key, double-submit |
| Campaigns | create | edit/send/delete/toggles, confirm-dialog flows |
| Uploads | upload+publish | re-process, preview/download/delete, knowledge-gap modal |
| Intents | none | all save/publish/delete actions |
| Orders | status filter | search debouncing |
| App Shell | hamburger, logout | tenant switcher, register, back navigation |

~6 real interactions tested out of 100+ buttons/controls across the app.
