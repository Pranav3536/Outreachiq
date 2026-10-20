# OutreachIQ Architecture

## Overview

OutreachIQ is a local-first, single-user Python + Streamlit application. No database, no cloud, no external APIs. All state is in files under `data/` and `runtime/`.

## Data Flow

```
Upload CSV/XLSX
    ↓
Contact Data Lab: map columns → clean → validate → dedup → export contacts_clean.csv
    ↓
Designation Explorer: categorise titles → filter → select → campaign_selection (session)
    ↓
Email Studio: edit template → preview → prepare campaign → prepared_campaign (session)
    ↓
Campaign Manager: test/real mode → run_batch → history JSON → runtime/campaigns/
    ↓
History & Reports: read-only view → export
```

The Outreach Assistant sits alongside Campaign Manager, inspecting data and proposing campaigns without sending.

## Module List

| Module | Responsibility |
|--------|---------------|
| `config.py` | Paths, env-var access, directory creation |
| `auth/` | bcrypt login, lockout tracker, credentials storage |
| `data/loader.py` | CSV/XLSX loading, upload save (timestamped) |
| `data/column_mapping.py` | Header matching, canonical field mapping, apply/save |
| `data/validation.py` | Email syntax validation, missing-field flags |
| `data/cleaning.py` | Non-destructive trim/case into `*_clean` columns |
| `data/duplicates.py` | Duplicate detection by email, exclusion flags (no deletion) |
| `data/quality_report.py` | Summary metrics, problem-rows table |
| `data/export.py` | CSV/XLSX export (valid + non-excluded by default) |
| `data/designation.py` | Rule-based title categorisation (editable dict) |
| `data/insights.py` | KPIs, chart data, eligible-for-campaign filter |
| `ml/labels.py` | Labelled CSV loading, append, export |
| `ml/features.py` | TF-IDF word + char n-gram FeatureUnion |
| `ml/classifier.py` | LogisticRegression pipeline, train/predict, rule fallback |
| `ml/evaluation.py` | Stratified train/test split, per-class metrics, confusion matrix |
| `ml/scoring.py` | Explainable priority score (0-100) with reasons |
| `ml/nlp.py` | Token frequency, top keywords per category |
| `ml/quality_intel.py` | ML-aware data quality summary |
| `email_tools/templates.py` | Named template JSON persistence, working copy |
| `email_tools/placeholders.py` | `{Placeholder}` rendering, fallbacks, ensure_sendable gate |
| `email_tools/attachments.py` | Resume PDF validation, save, build_attachment |
| `email_tools/campaign_prep.py` | Per-recipient rendering, exclusion, PreparedCampaign |
| `email_tools/smtp_config.py` | SmtpConfig (masked repr), credentials_status |
| `email_tools/message_builder.py` | RFC EmailMessage, header-injection rejection |
| `email_tools/smtp_sender.py` | send_one (test/real), run_batch, error classification |
| `campaigns/history_store.py` | FileHistoryStore (Protocol, atomic JSON, sent_keys) |
| `campaigns/reports.py` | Campaign/recipient dataframes, filters, exports, review notes |
| `assistant/tools.py` | Read-only inspection, quality, suggestions, proposals |
| `assistant/workflow.py` | Keyword command parser, state machine |
| `ui/theme.py` | All CSS in one function (white + light sage) |
| `ui/components.py` | page_header, chart helpers, load_contacts |
| `ui/pages/` | 7 Streamlit pages (Overview, Contact Lab, Explorer, ML, Email, Campaign Manager, History) |

## Design Decisions

- **Local-first**: all data in files, no cloud. Trade-off: no concurrency, no remote access. The `HistoryStore` Protocol allows SQLite to replace the file store without changing callers.
- **Rule baseline + TF-IDF/LogisticRegression**: the rule-based categorisation in `designation.py` works without any model. The ML classifier improves on rules when labelled data is available. If no model is trained, the system falls back to rules and says so — never presents an untrained model as working.
- **Controlled assistant**: the Outreach Assistant can inspect, summarise, suggest, and propose, but never sends email, never modifies data, and never auto-approves. Approval only copies a proposal's recipients into `campaign_selection`. Real sending stays exclusively in Campaign Manager with its own confirmation gate.
- **Non-destructive cleaning**: original columns are always preserved; `*_clean` columns are added alongside. Duplicates set an `excluded` flag; no rows are ever auto-deleted.
- **SMTP accepted is not delivery**: the app labels server acceptance as "SMTP Accepted", never "delivered". No open/reply/delivery stats exist anywhere.
- **No auto-retry**: ambiguous SMTP failures (Unknown/Needs Review) are never retried automatically. The user is told to check their Sent folder.
- **Two strictly separated send modes**: test mode makes zero network calls and returns "Simulated". Real mode uses STARTTLS or SMTP_SSL. Results carry their mode so a simulated result can never be shown as real.
