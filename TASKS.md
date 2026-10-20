# OutreachIQ - Task Checklist

## Phases

- [x] Phase 0: Foundation — folders, config, venv, git, smoke test
- [x] Phase 1: Shell + Theme + Login
- [x] Phase 1.5: UI polish + login autofill
- [x] Phase 2: Contact Data Lab
- [x] Phase 3: Dashboard + Designation Explorer
- [x] Phase 4: ML / NLP
- [x] Phase 5: Email Studio
- [x] Phase 6: Gmail SMTP + Sending
- [x] Phase 7: History / Reports + Assistant
- [x] Phase 8: Integration / Security / Docs

## Status Legend
Not Started / In Progress / Blocked / Completed

## Detailed Status

| Phase | Status | Notes |
|-------|--------|-------|
| 0 Foundation | Completed | folders, .env.example, gitignore (verified), venv, deps installed, 2/2 smoke tests pass, git init main |
| 1 Shell+Theme+Login | Completed | login gate, bcrypt+lockout, sage theme, 7 nav pages, scripts/create_user.py |
| 1.5 UI polish+autofill | Completed | polished centered login card, autocomplete attrs, sage sidebar w/ dark-green active item, page_header helper, hide footer/menu, all CSS in theme.py |
| 2 Contact Data Lab | Completed | 2a+2b: loader, mapping, validation, cleaning, duplicates (flag only), quality report, export CSV/XLSX; 3 synthetic sample CSVs; 55/55 tests pass |
| 3 Dashboard+Designation Explorer | Completed | designation.py (rule-based, editable dict), insights.py (KPIs/charts/agg), Overview Dashboard + Designation Explorer pages; friendly no-data message; campaign_selection stored; 20/20 tests pass |
| 4 ML/NLP | Completed | labels.py, features.py, classifier.py (TF-IDF+LR, rule fallback), evaluation.py (stratified, no leakage), nlp.py, scoring.py, quality_intel.py, templates_map.py; ML page (5 tabs); 16/16 tests pass |
| 5 Email Studio | Completed | 5a (templates.py, placeholders.py) + 5b (attachments.py, campaign_prep.py, email_studio page); 34+23=57 tests pass; no SMTP, no send button |
| 6 Gmail SMTP+Sending | Completed | 6a (smtp_config, message_builder, smtp_sender) + 6b (history_store, campaign_manager page, overview updated); 29+17=46 tests pass |
| 7 History/Reports+Assistant | Completed | 7a: reports + history page (20 tests) + 7b: assistant/tools.py, workflow.py, campaign_manager tab (28 tests); 48 total pass |
| UI Polish | Completed | Login layout fix: single centered card on sage bg (flex viewport-height centering); feature lines compact row; 2/2 login/app render tests pass |

## Phase 5b Summary

**Implemented:**
- `email_tools/attachments.py`: `validate_resume` (extension, %PDF magic, 5 MB limit, no path traversal), atomic `save_resume` → `runtime/resume/default_resume.pdf`, `resume_exists/meta/delete`, `build_attachment` returning (bytes, name, mimetype) for Phase 6.
- `email_tools/campaign_prep.py`: `prepare_campaign` renders per-recipient subject+body via `render_for_contact`, calls `ensure_sendable`, sends failing rows to excluded list with reasons (invalid email, missing email, excluded duplicate, unresolved placeholder). Enforces `MAX_RECIPIENTS_PER_CAMPAIGN` (default 100). Returns `PreparedCampaign`; session-state storage is in UI layer only.
- `ui/pages/email_studio.py`: 4 tabs (Template editor with load/save/delete/reset, live per-contact preview with fallback/unresolved warnings, resume upload/replace/delete with metadata, Summary & Prepare). Contacts source: `campaign_selection` → fallback to contacts_clean.csv valid rows. Auto-saves working template. No send button, no SMTP. Shows "Not sent. Go to Campaign Manager."
- `email_tools/__init__.py` updated to re-export all new symbols.
- `config.py` already had `EMAIL_TEMPLATES_DIR` (Phase 5a).

**Files created:** `email_tools/attachments.py`, `email_tools/campaign_prep.py`, `ui/pages/email_studio.py`, `tests/test_email_studio.py`.
**Files changed:** `email_tools/__init__.py`, `TASKS.md`, `PROJECT_STATE.md`.

**Test results:** 23/23 pass (0 failures, 0 warnings).

**Known bugs/limits:**
- `email_studio.py` uses `st.stop()` inside tabs; this works in Streamlit but stops rendering the rest of the page when no contacts are available. Acceptable for current scope.
- Template editor auto-saves on every keystroke via widget comparison; could cause extra writes on slow machines. Acceptable for local-first personal use.

**Decisions made:**
- Contacts from `campaign_selection` are taken as-is (already filtered valid+non-excluded by Designation Explorer / ML). If empty, a read-only fallback to `contacts_clean.csv` is offered.
- Resume file is always `runtime/resume/default_resume.pdf` (one file). No multi-resume management.
- `prepare_campaign` never writes to disk or session state; that is the UI layer's job.

**Next task:** Phase 6a — Gmail SMTP sender (test mode vs real mode).
- `email_tools/smtp_sender.py`: `SmtpConfig` from env vars; `test_connection()` (EHLO only, no message); `send_one(recipient, subject, body, attachment_bytes?)` — one email, one recipient, no batching here. Real mode: smtplib STARTTLS; test mode: log to `runtime/logs/` only, never connect. Never auto-retry on ambiguous failure. SMTP accepted ≠ delivered; log accordingly.
- Phase 6b: Campaign Manager page — load `prepared_campaign`, review list, send button (one at a time with configurable delay), per-recipient status (accepted/failed/skipped), history JSON written to `runtime/campaigns/`.

## Phase 6a Summary

**Implemented:**
- `smtp_config.py`: `SmtpConfig` dataclass with masked repr/str (password never visible), `load_smtp_config()` (validates email format, strips spaces from app password), `credentials_status()` (key names only).
- `message_builder.py`: `build_message()` — RFC-compliant EmailMessage, one To header (no Cc/Bcc), header injection rejection (newlines in subject/to raise `MessageBuildError`), PDF attachment via `add_attachment()`.
- `smtp_sender.py`: `send_one()` with strict test/real separation — test mode makes zero smtplib calls and returns `Simulated`; real mode uses STARTTLS. Error classification: `_FatalSendError` (auth) → stops batch; `_RateLimitError` (codes 421/450/451/452/454) → stops batch; `SMTPRecipientsRefused` → `Failed`, batch continues; timeout/disconnect → `Unknown/Needs Review`, no retry. `run_batch()`: injectable sleep, `already_sent_keys` dedup, `on_result` callback, `should_stop` signal, MAX_RECIPIENTS cap, pre-flight `ensure_sendable` re-check.
- `email_tools/__init__.py`: updated to re-export all new symbols.

**Files created:** `email_tools/smtp_config.py`, `email_tools/message_builder.py`, `email_tools/smtp_sender.py`, `tests/test_smtp.py`.
**Files changed:** `email_tools/__init__.py`, `TASKS.md`, `PROJECT_STATE.md`.

**Test results:** 29/29 pass (0 failures, 0 warnings). All smtplib calls mocked; no real connection ever made.

**Known bugs/limits:**
- `run_batch` in real mode requires `prepared_campaign.is_sendable` to be True; if the campaign has no ready recipients it raises. This is intentional gating.
- `_FatalSendError` and `_RateLimitError` are internal (prefixed `_`) but are imported in tests by name. This is acceptable; they are part of the stable behaviour contract.

**Decisions:**
- Password masked at `SmtpConfig` level so no downstream code can accidentally log it through repr/str.
- `send_one` returns `Unknown/Needs Review` on timeout/disconnect after sending data — the spec's requirement that ambiguous failures are never retried automatically is enforced architecturally (no retry loop anywhere).
- Test mode result carries `mode="test"` so it can never be presented in the UI as a real send outcome.

**Exact next task:** Phase 6b — Campaign Manager page
- UI in `ui/pages/campaign_manager.py`.
- Load `st.session_state["prepared_campaign"]`; if missing, show friendly message.
- Mode selector: "Test (simulate, no network)" / "Real (send via Gmail)".
- Real mode requires explicit confirmation checkbox + GMAIL_ADDRESS configured.
- Progress table: one row per recipient, status updates live via `on_result` callback.
- Send button triggers `run_batch` with configurable delay; stop button sets `should_stop`.
- On completion, write a campaign history JSON to `runtime/campaigns/<timestamp>.json` with: campaign_id, timestamp, mode, ready_count, results summary (no body content, no credentials).
- Show "SMTP Accepted is not inbox delivered" note prominently.

## Phase 6b Summary

**Implemented:**
- `campaigns/history_store.py`: `FileHistoryStore` implementing `HistoryStore` Protocol. Atomic JSON per campaign under `runtime/campaigns/`. Per-recipient update on every `on_result` callback. `sent_keys()` returns normalised emails that are SMTP Accepted or Unknown/Needs Review in real-mode campaigns only; simulated and failed rows excluded. `list_campaigns()` / `load_campaign()`. No body text or credentials stored.
- `campaigns/__init__.py`: exports `FileHistoryStore`, `HistoryStore`, `get_store`.
- `ui/pages/campaign_manager.py`: reads `prepared_campaign` from session state; mode selector (Test default / Real); pre-send panel (counts, excluded list, already-sent warning, sample preview, delay); real-mode blocking (credentials missing, campaign not sendable, over limit, ≥10 recipient warning); confirmation gate (checkbox + type recipient count); `run_batch` call with live results table, stop button, `on_result` writes to store immediately; fatal-error guidance; "SMTP Accepted ≠ delivered" note; never auto-retries Unknown rows.
- `ui/pages/overview.py`: "Campaign activity" section replaced with `FileHistoryStore` data (counts per status, "accepted_by_server" label); guarded `if _has_data:` blocks prevent `AttributeError` when no contacts loaded.

**Files created:** `campaigns/{__init__,history_store}.py`; `ui/pages/campaign_manager.py` (rewrite); `tests/test_campaign_manager.py`.
**Files changed:** `ui/pages/overview.py` (campaign section + `_has_data` guards); `TASKS.md`; `PROJECT_STATE.md`.

**Test results:** 17/17 pass (0 failures). All SMTP mocked; no real connection made. Bug found and fixed: `overview.py` crashed when no contacts due to `categorize(None)` after `st.stop()` — fixed with `if _has_data:` guards.

**Known bugs/limits:**
- Campaign Manager page runs `run_batch` synchronously in the Streamlit script; for large recipient lists the page will appear to hang until all sends complete. Async execution is out of scope for Phase 6; stop button mitigates this.
- The stop button works across reruns but not mid-send (Streamlit's execution model). For personal 10–20 recipient use this is acceptable.

**Decisions:**
- `sent_keys()` treats Unknown/Needs Review the same as Accepted for duplicate-send prevention (the message may have been received; safer to skip).
- Template body text is never stored in history records — only subject snippet (60 chars) and metadata.
- `HistoryStore` is a `Protocol` so `FileHistoryStore` can be swapped for SQLite without touching callers.

**Manual live-test steps (run after setting up .env):**
1. `python scripts/create_user.py` (if not done) → `streamlit run app.py`
2. Contact Data Lab → upload a CSV with 2–3 of your own email addresses → Map → Clean → Apply.
3. Designation Explorer → "Send selection to campaign" for those 2–3 rows.
4. Email Studio → verify template looks correct → preview for each → "Prepare campaign".
5. Campaign Manager → select **Test mode** first → press "Simulate send" → confirm all show "Simulated".
6. Campaign Manager → select **Real send (Gmail)** → check checklist → tick confirmation checkbox → type recipient count → press "Send".
7. Wait for results (delay between sends per `SEND_DELAY_SECONDS`). Check status column shows "SMTP Accepted".
8. Open Gmail (myaccount → Sent) → confirm 2–3 sent messages appear with correct subject/body.
9. Check inbox of the receiving addresses for delivery. SMTP Accepted ≠ guaranteed delivery.

**Next task:** Phase 7a — Campaign History & Reports page
- Full read-only view of all campaigns from `FileHistoryStore` (list + drill-down).
- Per-campaign detail: recipient table with statuses, subject snippet, mode, timestamps.
- Summary stats across all campaigns (total sent, accepted/failed/unknown, by mode).
- Export: campaign detail CSV/XLSX.
- Then Phase 7b: simple natural-language assistant (no LLM; keyword rules) for "how many sent", "show me failures", "export last campaign".

## Phase 6a Fix Summary

**Changes to smtp_sender.py:**
- Stage variable (`"connect"`, `"starttls"`, `"login"`, `"send"`) set before each network step.
- Port 465 → `SMTP_SSL` (no STARTTLS); all other ports → `SMTP + STARTTLS`.
- Errors at connect/starttls/login → status `"Failed"` + raise `_ConnectionFatalError` (message never sent; `run_batch` stops batch and marks remaining `Pending`).
- Errors at `"send"` only → `"Unknown/Needs Review"` (ambiguous; no auto-retry).
- `run_batch` adds key to `already_sent_keys` ONLY for `SMTP Accepted` or `Unknown/Needs Review` in real mode. `Failed`, `Pending`, `Simulated` never counted.
- `_ConnectionFatalError` added as third batch-stop sentinel alongside `_FatalSendError` and `_RateLimitError`.

**Files created:** `scripts/smtp_check.py`.
**Files changed:** `email_tools/smtp_sender.py`, `tests/test_smtp.py` (+12 tests).

**Test results:** 41/41 pass (29 existing + 12 new). 0 failures.

**Known limits:** `SMTP_SSL` context manager is tested via mock; actual SSL handshake not tested (requires real network). Acceptable for local-first personal use.

## Phase 7a Summary

**Implemented:**
- `campaigns/reports.py`: `campaigns_to_df()` (one row per campaign with counts), `recipients_df()` (per-recipient rows), `filter_campaigns()` / `filter_recipients()` (date range, mode, status, free-text search), `summary_stats()` (attempted/accepted/failed/unknown/simulated/pending — no delivery/open/reply keys), `export_csv_bytes()` / `export_xlsx_bytes()`, `save_review_note()` / `load_review_notes()` (atomic write to `runtime/campaigns/review_notes.json`). Corrupt JSON files skipped with warning list, never crash.
- `campaigns/__init__.py`: exports all report functions.
- `ui/pages/history_reports.py`: 4 tabs (Campaigns with drill-down, Recipients, Charts with Plotly sage palette, Needs Review with manual notes), summary metrics, filters (date/mode/status/search), CSV/XLSX download buttons, "SMTP Accepted ≠ delivered" note, friendly empty state, simulated rows clearly labelled.

**Files created:** `campaigns/reports.py`, `tests/test_reports.py`.
**Files changed:** `campaigns/__init__.py`, `ui/pages/history_reports.py` (full rewrite from placeholder), `TASKS.md`, `PROJECT_STATE.md`.

**Test results:** 20/20 pass (0 failures). Bug found and fixed: `created_at_dt` (timezone-aware datetime) crashed `to_excel` — fixed by dropping the helper column in `export_xlsx_bytes`.

**Known bugs/limits:** None. Corrupt JSON files are skipped with a warning; `review_notes.json` is excluded from campaign listings.

**Decisions:** `summary_stats` contains only counts the app actually knows (no delivery/open/reply rates). Review notes are stored separately from campaign records. The Needs Review tab has no resend button (manual review only).

**Next task:** Phase 7b — Controlled Outreach Assistant.
- `assistant/` module: keyword-based command parser (no LLM, no paid APIs).
- Commands: "how many sent", "show me failures", "export last campaign", "show needs review", "campaign summary".
- UI in a new tab or small panel on the History & Reports page.
- Tests: command parsing, response format, no network calls.

## Phase 7b Summary

**Implemented:**
- `assistant/tools.py`: `inspect_dataset()` (rows/columns/mapping status), `data_quality_summary()` (reuses build_report), `suggest_classifications()` (reuses ml/classifier with rule fallback), `selection_summary()` (category/company breakdown of campaign_selection, excludes invalid/excluded), `campaign_history_summary()` (reuses campaigns/reports — SMTP Accepted/Failed/Unknown/Simulated only, no delivery/open/reply), `propose_campaign()` (filters by category/limit, excludes invalid/duplicate/already-sent, checks template/resume/Gmail readiness, returns Proposal object, stores nothing).
- `assistant/workflow.py`: keyword-based `parse_command()` (check data, quality, suggest titles, selection, history, propose campaign for <categories> top <N>), `unknown_command_help()`, `WorkflowState` dataclass with transcript, state machine `next_state()`.
- `campaign_manager.py`: rewritten with two tabs. Tab 1 "Outreach Assistant": chat input, quick-action buttons, transcript, proposal card with exclusions table + approve/discard buttons. Approval only copies recipients to `st.session_state["campaign_selection"]` — no send button, no SMTP. Tab 2 "Send Campaign": existing send flow guarded by `if campaign is not None:` instead of `st.stop()` for AppTest safety.
- `assistant/__init__.py`: exports all public symbols.

**Files created:** `assistant/{__init__,tools,workflow}.py`, `tests/test_assistant.py`.
**Files changed:** `ui/pages/campaign_manager.py` (full rewrite with tabs), `TASKS.md`, `PROJECT_STATE.md`.

**Test results:** 28/28 pass (0 failures). smtplib never called; no file writes from tools; page renders with and without data.

**Known bugs/limits:**
- The assistant tab's `_handle_command` calls `st.rerun()` after each command, which is the standard Streamlit pattern. Acceptable.
- `propose_campaign` uses `eligible_for_campaign` which requires validation flag columns (email_valid, excluded) — if the contacts df lacks these, the proposal includes all rows. The UI's `load_contacts()` always adds flags, so this is safe in the app.

**Decisions:**
- No send button anywhere in the assistant. Approval only sets `campaign_selection`. Real send stays exclusively in Campaign Manager Tab 2 with its own confirmation gate.
- Tools are pure functions (no Streamlit imports) for testability. The UI layer passes the loaded df.
- `parse_command` uses keyword matching against CATEGORIES for the "propose" command, not regex, for robustness.
- No personal data in the transcript beyond counts and category names. No credentials anywhere.

**Next task:** Phase 8 — Integration, security review, docs.
- End-to-end smoke test of the full app (AppTest through all 7 pages).
- Security review: .env never printed, .gitignore verified, no credentials in logs/exceptions.
- README.md updated with full setup + usage instructions.
- requirements.txt pinned to installed versions.
- Final full test suite run.

## Phase 8 Summary

**Full test:** 254/254 pass (0 failures, 0 warnings). No unmocked SMTP connections. No real data reads.

**Security review (all pass):**
- .gitignore covers: .env, data/, runtime/ contents, *.pdf, *.csv, *.xlsx, *.joblib, *.pkl, *.log, review_notes.json, campaign records. Verified with `git check-ignore -v` on all sample paths.
- .env.example and sample_data/ NOT ignored (correct).
- `git ls-files`: no sensitive files tracked (no commits made yet).
- No hardcoded passwords/emails in source. SmtpConfig repr/str masks password (verified).
- No credential logging/printing anywhere.
- No auto-send or auto-retry paths. SMTP real mode requires explicit confirmation. send_one/run_batch only called from Campaign Manager.
- Login password is bcrypt-hashed only.
- Sample data and tests contain only synthetic data.

**Files created:** `README.md` (complete rewrite), `docs/ARCHITECTURE.md`.
**Files changed:** `TASKS.md`, `PROJECT_STATE.md`.

**Known limitations (honest list):**
- File-based storage (no concurrency, no remote access). HistoryStore Protocol designed for future SQLite swap.
- Rule-based assistant (no LLM, keyword matching only).
- ML metrics from synthetic data, not real contact distributions.
- SMTP Accepted is not inbox delivery.
- Gmail daily limit ~500 emails.
- run_batch is synchronous in Streamlit (page hangs during large batches; stop button works across reruns only).
- No open/reply/delivery stats (by design — the app only knows server acceptance).

**Suggested commit (do NOT run yet):**
```bash
git add .
git status   # verify no .env, resume, or credentials.json staged
git commit -m "feat: OutreachIQ v1 complete"
```

**No remaining issues. All phases complete.**

## UI Polish Summary

**Files changed:** `ui/theme.py` (premium CSS bundle: CSS variables, Inter + Fraunces fonts via Google Fonts @import, cards 12px radius + soft shadow, metric cards with green top accent + muted uppercase labels, sidebar sage-50 + active item sage-200 + 3px green left accent, buttons/inputs/tabs/dataframes/alerts/progress bars, fade-in 0.3s, responsive login), `ui/components.py` (CHART_COLORS extended to 5 sage tones, page_header with divider, style_plotly_fig with plotly_white template + Inter font + sage gridlines; bug fixed: marker_opacity→trace opacity selector), `.streamlit/config.toml` (toolbarMode minimal), `app.py` login (split-layout left sage panel + wordmark + 3 feature lines + right white form "Welcome back"; sidebar wordmark + signed-in caption + Logout).

**Bugs found and fixed:** (1) `update_traces(marker_opacity=0.9)` invalid for pie traces → replaced with `opacity=0.9, selector=dict(type="bar")`. (2) New CSS block inside f-string used unescaped `{}` → replaced with `{{}}`.

**Real test result:** 254/254 pass (0 failures after both fixes).

**Known limits:** Google Fonts load from CDN — offline use will fall back to system fonts. CSS selectors are conservative `data-testid` attributes; may need adjustment for future Streamlit versions. The `oi-real-send-block` amber tint requires the page to call `st.markdown(...unsafe_allow_html=True)` with the class manually if the distinction is wanted inside the tab; currently the Streamlit `st.warning()` provides the amber naturally. Login split-panel relies on Streamlit column CSS which can vary between versions.
