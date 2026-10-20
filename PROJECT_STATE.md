# OutreachIQ — Tasks & Development Log

## Current Status

- **Project:** OutreachIQ
- **Version:** v1
- **Status:** Core implementation marked complete in the project notes
- **Development approach:** Phases are recorded in the order they were implemented.
- **Testing:** The original project notes report 254 passing tests. Run `pytest` to verify the current result before relying on that count.

This file tracks the project phases, implementation notes, testing and decisions. Update it when a phase changes, a bug is fixed or a new feature is added. Keep completed work under its original phase instead of moving it to the top as a new task.

## Phase Overview

| Phase | Work | Recorded Status |
|---|---|---|
| Phase 1 | App Foundation and Authentication UI | Complete |
| Phase 2a | Contact Data Loading and Column Mapping | Complete |
| Phase 2b | Validation, Cleaning and Data Quality | Complete |
| Phase 3 | Overview and Designation Explorer | Complete |
| Phase 4 | ML/NLP and Contact Scoring | Complete |
| Phase 5a | Email Template Engine | Complete |
| Phase 5b | Email Studio and Resume Handling | Complete |
| Phase 6a | Gmail SMTP Sender | Complete |
| Phase 6b | Campaign Manager and History Store | Complete |
| Phase 7a | Campaign History and Reports | Complete |
| Phase 7b | Controlled Outreach Assistant | Complete |
| Phase 8 | Integration, Security and Documentation | Complete in the original notes |
| Post-v1 | Advanced UI Redesign | Recorded as completed |

---

## Phase 1 — App Foundation and Authentication UI

**Status:** Complete

### Work recorded
- Set up the Streamlit application structure and navigation.
- Added the login screen and authentication-related UI.
- Added shared UI components and a consistent sage-themed layout.
- Added common page headers and layout helpers.
- Kept the login form focused, with username/password autocomplete and Enter-key submission.

### Files recorded
- `app.py`
- `src/outreachiq/config.py`
- `src/outreachiq/auth/`
- `src/outreachiq/ui/theme.py`
- `src/outreachiq/ui/components.py`

### Verification
- Authentication and application-render tests were included in the test suite.
- Check the current repository and run the tests to verify the present implementation.

---

## Phase 2a — Contact Data Loading and Column Mapping

**Status:** Complete

### Work recorded
- Added CSV and Excel contact-data loading.
- Added support for mapping different column names to the expected contact fields.
- Added sample datasets with alternative column names for testing.
- Prepared the contact data for validation and cleaning in Phase 2b.

### Files recorded
- `src/outreachiq/data/loader.py`
- `src/outreachiq/data/column_mapping.py`
- `tests/test_loader.py`
- `tests/test_column_mapping.py`
- `sample_data/contacts_alt_names.csv`

### Verification
- Test contact loading with supported file formats.
- Test column mapping with alternative headers and missing expected columns.
- Use synthetic sample data for development tests.

---

## Phase 2b — Validation, Cleaning and Data Quality

**Status:** Complete

### Work recorded
- Added email syntax validation.
- Added non-destructive data cleaning. Original columns are retained, with cleaned values stored separately.
- Added duplicate handling with options to keep the first record, keep all records or exclude duplicates.
- Added data-quality reporting.
- Added CSV and Excel export.
- Added the option to apply cleaned data to `data/processed/contacts_clean.csv`.

### Files recorded
- `src/outreachiq/data/validation.py`
- `src/outreachiq/data/cleaning.py`
- `src/outreachiq/data/duplicates.py`
- `src/outreachiq/data/quality_report.py`
- `src/outreachiq/data/export.py`
- `tests/test_phase2b.py`

### Important decisions
- Cleaning should not silently delete the original data.
- Email validation checks syntax; it does not prove that an address exists or can receive mail.
- Duplicate handling should be explicit.
- Real contact data must not be committed to the public repository.

### Verification
- Test invalid and valid email formats.
- Test missing values and duplicate handling.
- Check that original columns remain available after cleaning.
- Check CSV and Excel exports.

---

## Phase 3 — Overview and Designation Explorer

**Status:** Complete

### Work recorded
- Added the Overview dashboard and designation-based contact exploration.
- Added contact insights, counts, filters and drill-down views.
- Added designation categorisation and eligibility-related rules.
- Added safeguards for empty or missing data.
- Kept the dashboard focused on contact and campaign information available in the application.

### Files recorded
- `src/outreachiq/data/designation.py`
- `src/outreachiq/data/insights.py`
- `src/outreachiq/ui/pages/overview.py`
- `src/outreachiq/ui/pages/designation_explorer.py`
- Updated `src/outreachiq/ui/components.py`

### Verification
- Test designation rules and insight calculations.
- Test page rendering with and without contact data.
- Campaign status labels must not imply delivery, opens or replies when that information is unavailable.

---

## Phase 4 — ML/NLP and Contact Scoring

**Status:** Complete

### Work recorded
- Added a labelled contact-title dataset using synthetic examples.
- Added classification and prediction utilities.
- Added a rule-based fallback when a trained model is unavailable.
- Added contact scoring with a score from 0 to 100 and explanatory reasons.
- Added keyword-frequency insights and template mapping.
- Added an ML/NLP page with separate tabs for the available features.
- Added checks to reduce the risk of training and test data overlap.

### Files recorded
- `src/outreachiq/ml/labels.py`
- `src/outreachiq/ml/features.py`
- `src/outreachiq/ml/classifier.py`
- `src/outreachiq/ml/evaluation.py`
- `src/outreachiq/ml/nlp.py`
- `src/outreachiq/ml/scoring.py`
- `src/outreachiq/ml/quality_intel.py`
- `src/outreachiq/ml/templates_map.py`
- `src/outreachiq/ui/pages/ml_nlp.py`
- `sample_data/labelled_titles_synthetic.csv`

### Verification
- Test labelled-data loading and export.
- Test training, prediction and the rule-based fallback.
- Test score ranges and scoring reasons.
- Test behaviour with small classes and missing data.
- Treat metrics based on synthetic data as development results, not proof of real-world performance.

---

## Phase 5a — Email Template Engine

**Status:** Complete

### Work recorded
- Added reusable email templates.
- Added placeholder detection and rendering.
- Added case-insensitive placeholder handling and fallback values.
- Added template validation and checks for unresolved placeholders.
- Added template save, load, list and delete operations.
- Added a sendability check to prevent sending templates with unresolved required content.

### Files recorded
- `src/outreachiq/email_tools/templates.py`
- `src/outreachiq/email_tools/placeholders.py`
- `src/outreachiq/email_tools/__init__.py`
- Updated `src/outreachiq/config.py`

### Verification
- Test placeholder detection and rendering.
- Test fallback values and unresolved placeholders.
- Test template validation and persistence.
- Test that invalid or incomplete templates fail the sendability check.

### Design decision
The template engine handles email content and validation. Sending functionality belongs to the later SMTP and campaign phases.

---

## Phase 5b — Email Studio and Resume Handling

**Status:** Complete

### Work recorded
- Added the Email Studio page.
- Added template editing and live preview.
- Added resume upload, validation, metadata and deletion utilities.
- Added per-recipient campaign preparation and placeholder rendering.
- Added recipient exclusion reasons and campaign-size checks.
- Added a sendability gate before a prepared campaign can move to the sending workflow.

### Files recorded
- `src/outreachiq/email_tools/attachments.py`
- `src/outreachiq/email_tools/campaign_prep.py`
- `src/outreachiq/ui/pages/email_studio.py`
- `tests/test_email_studio.py`

### Verification
- Test attachment validation and metadata handling.
- Test template rendering for individual recipients.
- Test unresolved placeholders and invalid campaign entries.
- Test the configured recipient limit.
- Confirm that campaign preparation itself does not send emails.

### Design decisions
- The default resume filename is `default_resume.pdf`.
- Prepared campaigns are validated before they reach the sending workflow.
- Resume files and private documents belong in local runtime storage, not GitHub.

---

## Phase 6a — Gmail SMTP Sender

**Status:** Complete

### Work recorded
- Added SMTP configuration and credential-status checks.
- Masked sensitive configuration values in representations.
- Added email message construction and PDF attachment support.
- Added header-injection checks and a single-recipient `To` header.
- Added separate test and real sending modes.
- Added error classification, batch processing, delays, stop handling and callbacks.
- Added recipient caps and deduplication checks.

### Files recorded
- `src/outreachiq/email_tools/smtp_config.py`
- `src/outreachiq/email_tools/message_builder.py`
- `src/outreachiq/email_tools/smtp_sender.py`
- `tests/test_smtp.py`

### Verification
- Test message construction and attachment handling.
- Test credential masking and error classification.
- Test batch processing, stop behaviour and deduplication.
- Keep tests independent of real SMTP connections.
- Do not automatically retry ambiguous SMTP outcomes, since the original message may already have been accepted.

### Important
**SMTP acceptance does not mean inbox delivery.** The application does not claim to track delivery, opens or replies.

---

## Phase 6b — Campaign Manager and History Store

**Status:** Complete

### Work recorded
- Added a campaign mode selector for test and real sending.
- Added a confirmation gate for real campaigns.
- Added checks for sender configuration before real sending.
- Added batch execution with per-recipient results, progress feedback, delay and stop control.
- Added persistent campaign history using JSON files.
- Added sent-key tracking to reduce duplicate sends.
- Updated the Overview dashboard to use campaign history when available.
- Added safeguards for missing campaign data.

### Files recorded
- `src/outreachiq/campaigns/history_store.py`
- `src/outreachiq/campaigns/__init__.py`
- Updated `src/outreachiq/ui/pages/campaign_manager.py`
- Updated `src/outreachiq/ui/pages/overview.py`
- `tests/test_campaign_manager.py`

### Verification
- Test history storage and duplicate tracking.
- Test campaign mode selection and real-send confirmation.
- Test successful, failed and ambiguous send outcomes.
- Test empty campaign history and missing data.
- Verify that campaign history does not store email body text or credentials.

### Known limitations
- Batch sending is synchronous, so the page can remain busy during a larger campaign.
- The stop control is subject to Streamlit rerun behaviour.
- File-based storage is used; the `HistoryStore` protocol leaves room for a future storage implementation.
- Unknown or Needs Review outcomes are handled conservatively for duplicate prevention.

### Manual test checklist
- [ ] Open Campaign Manager with no campaign history.
- [ ] Prepare a small synthetic campaign.
- [ ] Run test mode and verify that it does not send real emails.
- [ ] Verify that real mode requires explicit confirmation and valid sender configuration.
- [ ] Check that recipient statuses are recorded.
- [ ] Restart the app and check that saved campaign history can be loaded.
- [ ] Confirm that message bodies and credentials are not stored in history.

---

## Phase 7a — Campaign History and Reports

**Status:** Complete

### Work recorded
- Added campaign and recipient reporting utilities.
- Added a History & Reports page with four tabs: campaign history and drill-down, recipients, charts, and Needs Review.
- Added filters for date, mode, status and search.
- Added campaign summary statistics.
- Added CSV and Excel exports.
- Added separate manual review notes.
- Added handling for corrupt history JSON files, with warnings instead of an unhandled failure.

### Files recorded
- `src/outreachiq/campaigns/reports.py`
- `tests/test_reports.py`
- Updated `src/outreachiq/campaigns/__init__.py`
- Updated `src/outreachiq/ui/pages/history_reports.py`

### Verification
- Test campaign and recipient dataframes.
- Test filters and summary calculations.
- Test CSV and Excel export.
- Test handling of corrupt history records.
- Test manual review notes.

### Design decisions
- Do not display delivery, open or reply metrics that the application does not collect.
- Review notes are stored separately from campaign records.
- The Needs Review page does not provide a resend button.
- SMTP acceptance should be described accurately.

---

## Phase 7b — Controlled Outreach Assistant

**Status:** Complete

### Work recorded
- Added a keyword-based assistant without an LLM or paid AI API.
- Added tools for inspecting contact data, checking quality, making suggestions, selecting records, reviewing history and proposing a campaign.
- Added a command parser, workflow state and help for unrecognised commands.
- Added the assistant to Campaign Manager as a separate tab from sending.
- Added an approval flow that copies the proposed selection to `campaign_selection`.

### Files recorded
- `src/outreachiq/assistant/__init__.py`
- `src/outreachiq/assistant/tools.py`
- `src/outreachiq/assistant/workflow.py`
- `tests/test_assistant.py`
- Updated `src/outreachiq/ui/pages/campaign_manager.py`

### Example commands recorded
- `how many sent`
- `show failures`
- `export last campaign`
- `show needs review`
- `campaign summary`

### Verification
- Test recognised and unrecognised commands.
- Test assistant responses and selection logic.
- Verify that assistant tools do not make SMTP calls or write campaign files.
- Verify that the assistant cannot send a campaign directly.

### Design decisions
- Assistant tools are read-only.
- Approval changes the selected campaign; it does not send messages.
- Personal contact details and credentials should not be included in the assistant transcript.
- The UI should ensure the expected flag columns exist before proposing a campaign.

---

## Phase 8 — Integration, Security and Documentation

**Status:** Recorded as complete

### Work recorded
- Performed application integration checks.
- Reviewed environment-variable and secret-handling practices.
- Checked `.gitignore` and local configuration handling.
- Prepared project documentation, including the README and architecture notes.
- Ran the full test suite.

### Original final test record
- 254 tests reported passing.
- 0 failures reported.
- 0 warnings reported.

These numbers are from the original development notes. Run the current test suite before treating them as the latest verified result.

### Final verification checklist
- [ ] Run `pytest` and review the actual output.
- [ ] Start the application and check all seven pages.
- [ ] Verify login and logout behaviour.
- [ ] Verify that missing or empty contact data does not crash pages.
- [ ] Check `.gitignore` and `.env.example`.
- [ ] Confirm that real credentials, contact lists, resumes and private campaign history are not committed.
- [ ] Check README setup instructions against the current code.
- [ ] Confirm that test-mode execution does not send real email.
- [ ] Confirm that real sending requires explicit user action.
- [ ] Review the known limitations before presenting the project.

---

## Post-v1 — Advanced UI Redesign

**Status:** Recorded as completed after the core v1 phases

This work was recorded separately from the numbered Phase 1–8 implementation sequence.

### Work recorded
- Updated the Streamlit theme and layout.
- Added a darker sidebar and revised tab styling.
- Added a redesigned login card and shared UI styling tokens.
- Updated shared components and the Plotly theme.
- Improved the campaign-history view, including campaign drill-down and recipient status details.
- Added summary statistics and CSV/XLSX export for campaign details.
- Kept the Outreach Assistant keyword-based and separate from the send workflow.

### Files recorded
- `.streamlit/config.toml`
- `src/outreachiq/ui/theme.py`
- `src/outreachiq/ui/components.py`
- `app.py`

### Recorded limitations
- Sidebar icons were not supported by the recorded `st.navigation` version.
- The split login layout was unstable, so a single-card layout was used.
- Rounded bar corners were not supported by the recorded Plotly version.

The original notes report 254 passing tests after this redesign. Re-run the tests to confirm the current state.

---

## Running the Project

From the project root in PowerShell:

```powershell
python -m venv .venv
.venv\Scripts\Activate.ps1
pip install -r requirements.txt
python scripts/create_user.py
streamlit run app.py
```

Run `python scripts/create_user.py` only when creating the local user for the first time.

Run the test suite with:

```powershell
pytest
```

## Environment Configuration

The project notes list these environment-variable names:

- `GMAIL_ADDRESS`
- `GMAIL_APP_PASSWORD`
- `SENDER_DISPLAY_NAME`
- `SMTP_HOST`
- `SMTP_PORT`
- `MAX_RECIPIENTS_PER_CAMPAIGN`
- `SEND_DELAY_SECONDS`

Configure actual values locally. Never commit passwords, app passwords or other secrets to GitHub.

## Development and Safety Rules

- Keep phases in chronological order.
- Update the relevant phase when implementation or test results change.
- Do not mark a feature complete unless the implementation and tests support that claim.
- Use synthetic data in automated tests.
- Never put private contact lists, resumes, credentials or real campaign records in the public repository.
- Do not treat SMTP acceptance as proof of delivery.
- Do not claim open or reply tracking unless it is actually implemented.
- Test sending logic without making real SMTP connections.
- Keep real sending behind explicit user confirmation.
- Record known limitations rather than hiding them.

## Current Follow-up

The original project notes mark the numbered phases and post-v1 UI redesign as complete. No new implementation task is listed here as pending by default.

Before adding new work, run the tests, check the current repository and record the next task below.

### Next Task

- [ ] No new task recorded. Add one here when the next piece of work is decided.

### Update Log

When making future changes, add a short entry with the date, files changed, tests run and any remaining limitations.

| Date | Change | Tests / Notes |
|---|---|---|
| — | Initial phase history consolidated in chronological order | Historical results are recorded above; rerun tests to verify current status |
