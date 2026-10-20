<div align="center">

# OutreachIQ

**Smart Outreach Intelligence Platform**

![Python](https://img.shields.io/badge/Python-3.10+-3B7A57?style=flat&logo=python&logoColor=white)
![Streamlit](https://img.shields.io/badge/Streamlit-App-2F5D42?style=flat&logo=streamlit&logoColor=white)
![scikit-learn](https://img.shields.io/badge/scikit--learn-ML-4E9A6C?style=flat&logo=scikitlearn&logoColor=white)
![Tests](https://img.shields.io/badge/tests-254%20passing-3B7A57?style=flat)
![Storage](https://img.shields.io/badge/storage-local%20files-9CCDAE?style=flat)

</div>

A personal-use, local-first Python + Streamlit app for contact data cleaning, EDA, explainable ML/NLP classification, template-based personalised email outreach via your own Gmail SMTP, and file-based campaign history. No paid APIs, no database, no LLM. All data stays on your machine.

**Quick links:** [Features](#features) · [Folder Structure](#folder-structure) · [Install](#install) · [Local Login Setup](#local-login-setup) · [Gmail Setup](#gmail-setup) · [Running the App](#running-the-app) · [Testing](#testing) · [Limitations](#limitations) · [Troubleshooting](#troubleshooting) · [Privacy](#privacy)

---

## Features

| Module | What it does |
|--------|--------------|
| **Contact Data Lab** | Upload CSV/XLSX, map columns to a canonical schema (name, email, title, company), clean and validate emails, flag duplicates, export. |
| **Overview Dashboard** | KPIs, charts, data quality indicators, campaign activity summary. |
| **Designation Explorer** | Rule-based job-title categorisation, filter by category/company/title, build a campaign selection. |
| **ML & NLP Intelligence** | TF-IDF + LogisticRegression title classifier with rule-based fallback, stratified evaluation, explainable priority scoring, keyword analysis. **Metrics come from synthetic labelled titles and do not represent real contact data.** |
| **Email Studio** | Template editor with `{Name}`, `{Company}`, `{Title}` placeholders, live per-contact preview, resume (PDF) upload, "Prepare campaign" gate. |
| **Campaign Manager** | Test mode (no email sent) and real send mode (Gmail SMTP). Per-recipient status tracking, stop button, campaign history records. |
| **Campaign History & Reports** | Read-only campaign list, drill-down, filters, charts, review notes, CSV/XLSX export. |
| **Outreach Assistant** | Keyword-based command parser (no LLM) for inspecting data, quality summary, suggestions, and campaign proposals. Never sends email; approval only copies recipients to a selection. |

---

## Folder Structure

```
outreach-iq/
├── app.py                     # Streamlit entry point (login + navigation)
├── requirements.txt
├── pytest.ini
├── .env.example                # Copy to .env and fill in
├── .streamlit/config.toml      # Theme (white + light sage)
├── scripts/
│   ├── create_user.py          # Create a local login user
│   └── smtp_check.py           # Test SMTP connection (no email sent)
├── src/outreachiq/
│   ├── config.py               # Paths and env-var access
│   ├── auth/                   # bcrypt login + lockout
│   ├── data/                   # loader, mapping, validation, cleaning, duplicates, quality, export, designation, insights
│   ├── ml/                     # labels, features, classifier, evaluation, scoring, nlp, quality_intel
│   ├── email_tools/            # templates, placeholders, attachments, campaign_prep, smtp_config, message_builder, smtp_sender
│   ├── campaigns/              # history_store, reports
│   ├── assistant/              # tools, workflow
│   └── ui/                     # theme, components, pages/
├── sample_data/                # Synthetic CSV/XLSX for testing
├── tests/                      # pytest suite
├── data/                       # uploads, processed, labelled (gitignored)
└── runtime/                    # campaigns, resume, models, logs, auth, email_templates (gitignored)
```

---

## Install

```bash
python -m venv .venv
.venv\Scripts\Activate.ps1   # Windows PowerShell
pip install -r requirements.txt
```

---

## Local Login Setup

```bash
python scripts/create_user.py
```

Choose a username and password (hidden input, min 8 characters). The bcrypt hash is stored in `runtime/auth/credentials.json` (gitignored). Then run the app and log in.

---

## Gmail Setup

1. Enable **2-Step Verification** on your Google account: [myaccount.google.com](https://myaccount.google.com/security).
2. Generate an **App Password**: myaccount.google.com → Security → App passwords → choose "Mail" → generate. Copy the 16-character password.
3. Copy `.env.example` to `.env` and fill in:
```
   GMAIL_ADDRESS=your_address@gmail.com
   GMAIL_APP_PASSWORD=your_16_char_app_password
   SENDER_DISPLAY_NAME=Your Name
   SMTP_HOST=smtp.gmail.com
   SMTP_PORT=587
   MAX_RECIPIENTS_PER_CAMPAIGN=100
   SEND_DELAY_SECONDS=5
```
4. Test the connection (no email sent):
```bash
   python scripts/smtp_check.py
```
   Prints `OK` or `FAILED at <stage>: <ExceptionClassName>`.

---

## Running the App

```bash
streamlit run app.py
```

---

## Uploading Data

Go to **Contact Data Lab** → upload a CSV or XLSX file. The app saves the original unchanged to `data/uploads/`, suggests a column mapping, and lets you confirm. After mapping, clean and validate: trim/case-fix names and companies, validate emails (syntax only), flag duplicates, export to `data/processed/contacts_clean.csv`.

Try the synthetic files in `sample_data/` (contacts_messy.csv, contacts_alt_names.csv, contacts_dirty.csv).

---

## Designation Explorer

Browse contacts by job-title category. The rule-based categorisation maps titles to: HR/Recruiting, Talent Acquisition, Founder/CEO/Owner, Director/Head, Manager, Other/Unknown. Rules are in a plain dict at the top of `src/outreachiq/data/designation.py` — edit them to suit your needs. Select contacts and "Send selection to campaign" stores them for Email Studio.

---

## ML & NLP Intelligence

Train a TF-IDF + LogisticRegression classifier on labelled titles (`sample_data/labelled_titles_synthetic.csv` or your own). The evaluation uses a stratified train/test split with no data leakage. **Metrics come from synthetic labelled titles and do not represent real contact data.** Priority scores (0-100) are explainable with per-contact reasons — called "priority score", never a response or hiring probability.

---

## Email Studio and Resume

Compose a template with `{Name}`, `{Company}`, `{Title}` placeholders. Fallbacks fill blanks (Hiring Team, your organization, your role). Upload a resume PDF (max 5 MB) to `runtime/resume/`. Click "Prepare campaign" to render per-recipient emails and check for unresolved placeholders. No email is sent from this page.

---

## Campaign Manager

- **Test mode** (default): simulates sending, makes zero network calls, all results show "Simulated".
- **Real send mode**: requires Gmail configured, campaign ready, and explicit confirmation (checkbox + type recipient count). Sends one email per recipient with a configurable delay. Stop button available. Per-recipient status: SMTP Accepted, Failed, Unknown/Needs Review, Pending.

> **SMTP Accepted means Gmail's server accepted the message. It does not confirm inbox delivery. Check your Gmail Sent folder.**

---

## History & Reports

Read-only view of all past campaigns. Drill into a campaign to see per-recipient statuses. Filter by date, mode, status, or search. Add manual review notes for Unknown/Needs Review rows. Export CSV/XLSX.

---

## Testing

```bash
pytest
```

All 254 tests use synthetic data and mocked SMTP — no real emails are ever sent in tests.

---

## Limitations

- **SMTP Accepted is not inbox delivery.** Gmail accepting the message does not guarantee the recipient received it. Check your Gmail Sent folder.
- **Gmail daily limits**: personal Gmail accounts have ~500 emails/day. Sending large batches may be rate-limited or flagged as spam.
- **File-based storage**: campaign history, templates, models, and resume are stored as files in `runtime/`. This is simple and local-first but does not scale to high concurrency. The `HistoryStore` Protocol in `campaigns/history_store.py` is designed so SQLite can replace the file store later without changing callers.
- **Rule-based assistant**: the Outreach Assistant uses keyword matching, not an LLM. It can inspect, summarise, suggest, and propose — but cannot hold a free-form conversation.
- **ML metrics from synthetic data**: classification metrics reflect the synthetic labelled dataset, not real contact distributions.

---

## Troubleshooting

| Problem | What to do |
|---------|-----------|
| `SMTPServerDisconnected` at connect | Check your network, firewall, or VPN. Run `python scripts/smtp_check.py`. |
| Login failed (auth error) | Regenerate your App Password at myaccount.google.com. Ensure 2-Step Verification is on. Spaces in the App Password are stripped automatically. |
| No resume found | Upload a PDF in Email Studio → Resume tab. Max 5 MB, must start with `%PDF`. |
| Unknown/Needs Review status | The message may or may not have been received. Check your Gmail Sent folder. Do NOT auto-retry — it could cause duplicate sends. |
| Page shows "no data" | Upload and clean contacts in Contact Data Lab first, or check that `data/processed/contacts_clean.csv` exists. |

---

## Privacy

- All data stays local. No cloud, no telemetry, no analytics.
- `.env`, resume PDF, contact files, campaign history, and credentials are gitignored.
- Passwords are bcrypt-hashed, never stored in plaintext.
- SMTP App Password is masked in all `repr`/`str` output and never logged.
- No test reads real data or opens real SMTP connections.

---

<div align="center">

Built by **Pranav Shrivastav** · [GitHub](https://github.com/Pranav3536)

</div>
