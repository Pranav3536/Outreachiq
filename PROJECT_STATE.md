# OutreachIQ - Project State

## Current Phase
Phase 8: Integration, Security, Docs (Completed) -> OutreachIQ v1 complete

## Final State
All 8 phases complete. 254 tests pass. Security review clean. README + ARCHITECTURE.md written.

## Run / Resume Instructions
- `python -m venv .venv ; .venv\Scripts\Activate.ps1 ; pip install -r requirements.txt`
- `python scripts/create_user.py` (first time only)
- `streamlit run app.py`
- `pytest` (254 tests, all synthetic, no real SMTP)

## Env Var NAMES (never values)
GMAIL_ADDRESS, GMAIL_APP_PASSWORD, SENDER_DISPLAY_NAME, SMTP_HOST, SMTP_PORT, MAX_RECIPIENTS_PER_CAMPAIGN, SEND_DELAY_SECONDS

## Test Count
254 tests across 10 test files. 0 failures. 0 warnings.

## Known Limitations
File-based storage (HistoryStore Protocol for future SQLite); rule-based assistant (no LLM); ML metrics from synthetic data; SMTP Accepted ≠ inbox delivery; Gmail daily limit ~500; synchronous batch sending; no open/reply/delivery stats.

## Phase 7b Summary
**Implemented:** assistant/tools.py (inspect, quality, suggest, selection, history, propose_campaign — all read-only), assistant/workflow.py (keyword parser, state machine, unknown-command help), campaign_manager.py (2 tabs: assistant + send; approval copies to campaign_selection only, no send button).
**Files created:** assistant/{__init__,tools,workflow}.py, tests/test_assistant.py.
**Files changed:** ui/pages/campaign_manager.py.
**Test results:** 28/28 pass. No smtplib calls. No file writes from tools.
**Known bugs/limits:** propose_campaign includes all rows if flag columns missing (UI always adds them — safe).
**Decisions:** no send button in assistant; approval only sets campaign_selection; tools are pure functions; no personal data in transcript; no credentials.

## Next Task
Phase 8: Integration, security review, docs.
- End-to-end AppTest through all 7 pages.
- .gitignore + .env security verification.
- README + requirements pin.
- Final full test suite.

## Phase 7a Summary
**Implemented:** campaigns/reports.py (campaigns_to_df, recipients_df, filters, summary_stats, CSV/XLSX export, review notes); history_reports page (4 tabs: Campaigns+drill-down, Recipients, Charts, Needs Review+manual notes); filters (date/mode/status/search); corrupt JSON skipped with warnings.
**Files created:** campaigns/reports.py, tests/test_reports.py.
**Files changed:** campaigns/__init__.py, ui/pages/history_reports.py, TASKS.md, PROJECT_STATE.md.
**Test results:** 20/20 pass. Bug fixed: export_xlsx_bytes crashed on tz-aware datetime — dropped helper column.
**Known bugs/limits:** None.
**Decisions:** no delivery/open/reply stats anywhere; review notes stored separately; no resend button in Needs Review.

## Next Task
Phase 7b: Controlled Outreach Assistant
- assistant/ module: keyword-based command parser (no LLM, no paid APIs).
- Commands: "how many sent", "show failures", "export last campaign", "show needs review", "campaign summary".
- UI panel on History & Reports page or new page.
- Tests: command parsing, response format, no network.

## Phase 6b Summary
**Implemented:** campaigns/history_store.py (FileHistoryStore, atomic JSON, sent_keys dedup, HistoryStore Protocol); campaign_manager.py (mode selector, pre-send panel, real-mode confirmation gate, run_batch + live results, stop button, fatal-error guidance, "Accepted ≠ delivered" note); overview.py updated with real store data + _has_data guards.
**Files created:** campaigns/{__init__,history_store}.py; ui/pages/campaign_manager.py; tests/test_campaign_manager.py.
**Files changed:** ui/pages/overview.py.
**Test results:** 17/17 pass. Bug fixed: overview crashed on categorize(None) — fixed with _has_data guard.
**Known limits:** run_batch is synchronous (page hangs during large batches); stop button works across reruns only. Acceptable for ≤100 personal use.
**Decisions:** Unknown/Needs Review counts toward sent_keys (safer); no body text in records; HistoryStore is a Protocol for future SQLite swap.
**Manual test steps:** see full TASKS.md Phase 6b Summary section.

## Advanced UI Redesign (post v1)
Files changed: .streamlit/config.toml, ui/theme.py (dark sidebar, pill tabs, login card, force light, tokens), ui/components.py (new helpers, Plotly template), app.py (login features, dark sidebar markup).
Test result: 254/254 pass. Limits: sidebar icons not supported by st.navigation in 1.65; split login unstable → single card; bar rounded corners not in Plotly 7.x.
- Full read-only view of all campaigns from FileHistoryStore (list + drill-down).
- Per-campaign detail: recipient table with statuses, subject snippet, mode, timestamps.
- Summary stats across campaigns. Export detail CSV/XLSX.
- Phase 7b: keyword-rules assistant ("how many sent", "show failures", "export last campaign").

## Phase 6a Summary
**Implemented:** smtp_config.py (masked repr, credentials_status), message_builder.py (header injection rejection, one To, PDF attachment), smtp_sender.py (test/real separation, error classification, run_batch with injectable sleep/stop/callback/dedup/cap).
**Files created:** email_tools/{smtp_config,message_builder,smtp_sender}.py; tests/test_smtp.py.
**Files changed:** email_tools/__init__.py.
**Test results:** 29/29 pass. Zero real smtplib connections made.
**Known bugs/limits:** _FatalSendError/_RateLimitError are internal but imported in tests — acceptable. run_batch raises if campaign not sendable — intentional.
**Decisions:** password masked at SmtpConfig level; Unknown/Needs Review on post-DATA ambiguity with no retry; mode="test" result can never be presented as real.

## Next Task
Phase 6b: Campaign Manager page
- Load prepared_campaign from session_state; friendly message if missing.
- Mode selector: Test / Real (Real requires confirmation + GMAIL_ADDRESS set).
- run_batch with live progress table, stop button, configurable delay.
- Write history JSON to runtime/campaigns/ (no body content, no credentials).
- "SMTP Accepted is not inbox delivered" shown prominently.

## Phase 5b Summary
**Implemented:** attachments.py (validate/save/meta/delete/build_attachment), campaign_prep.py (prepare_campaign: per-recipient render, ensure_sendable gate, MAX_RECIPIENTS limit, exclusion reasons), email_studio page (4 tabs: template editor, live preview, resume, summary+prepare).
**Files created:** email_tools/{attachments,campaign_prep}.py; ui/pages/email_studio.py; tests/test_email_studio.py.
**Files changed:** email_tools/__init__.py.
**Test results:** 23/23 pass (0 failures).
**Known bugs/limits:** st.stop() inside tabs stops full-page render when no data — acceptable. Template auto-save on keypress — acceptable for local use.
**Decisions:** single resume file (default_resume.pdf); contacts source = campaign_selection with fallback to contacts_clean.csv; prepare_campaign is pure logic (no session/disk writes).
**No SMTP, no send button anywhere in Phase 5.**

## Next Task
Phase 6a: Gmail SMTP sender (test mode vs real mode)
- email_tools/smtp_sender.py: SmtpConfig from env; test_connection() EHLO only; send_one(recipient, subject, body, attachment?) with STARTTLS real mode and log-only test mode. Never auto-retry ambiguous failures. SMTP accepted != delivered.
- Phase 6b: Campaign Manager page — load prepared_campaign, one-at-a-time send with delay, per-recipient status, history JSON to runtime/campaigns/.

## Phase 5a notes
Files created: email_tools/{__init__,templates,placeholders}.py.
Files changed: config.py (EMAIL_TEMPLATES_DIR path + ensure_dirs).
Test results: 34/34 pass (default template content, find_placeholders, render, case-insensitive, fallbacks, unresolved, ensure_sendable raises, validate_template, save/load/list/delete, working-copy persistence).
Known bugs: none.

## Next Task
Phase 5b: Email Studio UI + resume upload
- Email Studio page: sidebar template list (load/save/delete), subject+body editors prefilled with working copy, per-contact preview table (Name, Company, rendered subject, first 100 chars of body, used_fallbacks, unresolved).
- Resume upload: single PDF upload to runtime/resume/ (one file only, replace on re-upload, gitignored). Show filename and upload date; never read or display its contents.
- "Prepare campaign" button: render all contacts from campaign_selection, gate on ensure_sendable, show count of ready/blocked rows; store ready rows in st.session_state["campaign_ready"]. No sending yet.
- Tests: page renders with and without campaign_selection (AppTest); prepare campaign blocks rows with unresolved placeholders.

## Phase 4 notes
Files created: ml/{__init__,labels,features,classifier,evaluation,nlp,scoring,quality_intel,templates_map}.py; ui/pages/ml_nlp.py (5-tab page); sample_data/labelled_titles_synthetic.csv (200+ rows synthetic).
Files changed: ml/__init__.py wired all exports.
Test results: 16/16 pass (labelled load/append/export, train+predict, needs_review flag, rule fallback without model, no train/test overlap, small-class warning, score 0-100 + reasons, keyword frequency, AppTest with+without data).
Known bugs: none. sklearn FutureWarning for multi_class fixed.
SMTP/delivery discipline: no open/reply/delivery stats anywhere in Phase 4.

## Next Task
Phase 5a: Template engine
- Template file format: plain-text .txt with {placeholders} (e.g. {name}, {company}).
- render_template(template_str, row_dict) -> filled string; raise TemplateError if any {placeholder} is unresolved or maps to blank.
- list_templates() and load_template() from runtime/templates/.
- preview_template(template, df) -> list of filled strings for first N rows.
- Email Studio UI: list templates, edit/create, preview with first matched row, no sending.
- Tests: valid fill, missing field raises TemplateError, blank value raises, no unresolved {} in output, preview truncates safely.

## Folder Tree
```
outreach-iq/
├── .kiro/steering/project.md
├── .streamlit/config.toml                 # sage theme + toolbarMode minimal
├── .env.example, .gitignore, pytest.ini
├── app.py                                  # polished login card + nav + logout
├── requirements.txt, README.md, TASKS.md, PROJECT_STATE.md
├── scripts/create_user.py
├── src/outreachiq/
│   ├── __init__.py, config.py
│   ├── auth/{__init__.py, credentials.py, lockout.py}
│   ├── data/{__init__.py, loader.py, column_mapping.py,     # 2a
│   │         validation.py, cleaning.py, duplicates.py,    # 2b
│   │         quality_report.py, export.py}
│   ├── ui/{__init__.py, theme.py, components.py}            # 1.5
│   │   └── pages/{overview,contact_lab,designation_explorer,ml_nlp,
│   │            email_studio,campaign_manager,history_reports}.py
│   └── {ml,email_tools,campaigns,assistant}/__init__.py
├── tests/{test_smoke,test_auth,test_config,
│          test_loader,test_column_mapping,test_contact_lab_page,
│          test_phase2b,test_app_render}.py
├── sample_data/{contacts_messy,contacts_alt_names,contacts_dirty}.csv  # synthetic
├── docs/.gitkeep
├── data/{uploads,processed,labelled}/.gitkeep
└── runtime/{campaigns,resume,models,logs,auth}/.gitkeep
```

## Environment Variables (names only; see .env.example)
- GMAIL_ADDRESS, GMAIL_APP_PASSWORD, SENDER_DISPLAY_NAME,
- SMTP_HOST, SMTP_PORT, MAX_RECIPIENTS_PER_CAMPAIGN, SEND_DELAY_SECONDS

## Run Commands
- Create venv: `python -m venv .venv`
- Activate (pwsh): `.venv\Scripts\Activate.ps1`
- Install deps: `pip install -r requirements.txt`
- Create a local user: `python scripts/create_user.py` (hidden password input)
- Run app: `streamlit run app.py`
- Run tests: `pytest`

## Phase 3 notes
Files created: data/designation.py, data/insights.py (no ML), ui/pages/overview.py, ui/pages/designation_explorer.py.
Files changed: data/__init__.py (exports), ui/components.py (load_contacts, chart helpers).
Test results: 20/20 pass (designation rules, insights, eligibility, AppTest both pages with+without data).
Known bugs: none.
SMTP label confirmed: all campaign history rendered as "accepted by server", never "delivered/open/replied".

## Next Task
Phase 5a: Template engine
- Template file format (plain-text .txt with {placeholders}).
- render_template(template_str, row_dict) -> filled string; raise TemplateError on any unresolved {placeholder}.
- List and load templates from runtime/templates/; preview with first matched contact row.
- UI in Email Studio page (no sending yet).
- Tests: valid fill, missing field raises, no unresolved placeholders in output.
- Login: centered white card (~420px), sidebar hidden, autocomplete="username"/"current-password", full-width green Sign in, Enter submits.
- App: sage sidebar with dark-green active item, page_header(title, subtitle) on all 7 pages, white bordered cards, footer+main menu hidden.
- 2b: validation (email-validator syntax-only) + cleaning (non-destructive, *_clean columns, originals kept) + duplicates (flag only, keep_first/keep_all/exclude) + quality report + CSV/XLSX export. Apply saves data/processed/contacts_clean.csv. Nothing auto-deleted.

## Next Task
Phase 3: Dashboard + Designation Explorer
- Overview Dashboard: KPIs (total/valid contacts, companies, duplicates) from data/processed/contacts_clean.csv.
- Designation Explorer: filter/sort by title/company, counts, drill-down.
- Reuse data/quality_report; read only saved cleaned files; no new writes to uploads.
