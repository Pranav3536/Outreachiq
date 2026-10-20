# OutreachIQ

**Smart Outreach Intelligence Platform**

![Python](https://img.shields.io/badge/Python-3.10+-3B7A57?style=flat&logo=python&logoColor=white)
![Streamlit](https://img.shields.io/badge/Streamlit-App-2F5D42?style=flat&logo=streamlit&logoColor=white)
![scikit-learn](https://img.shields.io/badge/scikit--learn-ML-4E9A6C?style=flat&logo=scikitlearn&logoColor=white)
![Storage](https://img.shields.io/badge/Storage-Local%20Files-9CCDAE?style=flat)

OutreachIQ is a personal project built with Python and Streamlit to manage contact data, explore job titles, use basic ML/NLP techniques, and prepare personalized emails through Gmail SMTP.

The application runs locally and stores its data in files. It does not require paid APIs, a database, or an LLM.

## Table of Contents

- [Features](#features)
- [Tech Stack](#tech-stack)
- [Folder Structure](#folder-structure)
- [Installation](#installation)
- [Local Login Setup](#local-login-setup)
- [Gmail Setup](#gmail-setup)
- [Running the App](#running-the-app)
- [Uploading and Cleaning Data](#uploading-and-cleaning-data)
- [Designation Explorer](#designation-explorer)
- [ML & NLP Intelligence](#ml--nlp-intelligence)
- [Email Studio and Resume](#email-studio-and-resume)
- [Campaign Manager](#campaign-manager)
- [Campaign History & Reports](#campaign-history--reports)
- [Outreach Assistant](#outreach-assistant)
- [Testing](#testing)
- [Limitations](#limitations)
- [Troubleshooting](#troubleshooting)
- [Privacy & Security](#privacy--security)

---

**Why I Built This**

Finding relevant people to contact for internships and job opportunities involves more than just writing an email. Contact lists often have inconsistent column names, missing details, duplicate records, and job titles that are difficult to categorize. Writing personalized emails and keeping track of outreach activity can also become repetitive when everything is managed separately.

I built OutreachIQ to bring these tasks into one place instead of switching between spreadsheets, email drafts, and campaign records.

**The Problem**

- **Messy contact data:** Contact lists from different sources may have different column names, missing information, invalid email formats, or duplicate entries.
- **Finding relevant contacts:** Job titles vary across companies, making it harder to identify HR professionals, recruiters, founders, and other relevant contacts.
- **Repetitive email writing:** Sending similar application emails to multiple people requires repeatedly updating names, company details, and other information.
- **Limited campaign tracking:** Without organized records, it can be difficult to review which messages were simulated, accepted by the SMTP server, failed, or need further attention.
- **Manual preparation:** Reviewing contacts, personalizing messages, attaching a resume, and checking recipients takes time when these tasks are handled separately.

**The Solution**

OutreachIQ combines these steps in a single Streamlit application. It allows me to import contact data, clean and categorize records, analyze job titles using basic ML/NLP techniques, prepare personalized emails, and review campaign activity.

Before sending a real campaign, recipients and email content can be reviewed, and sending requires explicit confirmation. Test mode is available to check the workflow without sending real emails.

The application uses Python, rule-based logic, and selected machine learning techniques. It runs locally, uses file-based storage, and does not depend on paid APIs or an LLM.

**How It Works**

1. **Import and clean contacts** — Upload a CSV or Excel file, map columns, validate email formats, identify duplicates, and review data quality.
2. **Explore job titles** — Categorize contacts using rules and filter them by designation, company, or category.
3. **Analyze and prioritize** — Use TF-IDF, Logistic Regression, rule-based fallbacks, and scoring to help review job titles and contact relevance.
4. **Prepare personalized emails** — Use reusable templates, preview recipient-specific messages, and attach a resume PDF.
5. **Review and send** — Simulate a campaign or explicitly approve real Gmail SMTP sending.
6. **Track campaign activity** — Review recipient statuses, inspect campaign history, add review notes, and export reports.

The aim is to reduce repetitive preparation work and make outreach easier to review and manage. OutreachIQ does not automate job applications independently, guarantee email delivery, or predict whether a recruiter will respond.
---

## Features

| Module | Description |
|---|---|
| **Overview Dashboard** | Displays key metrics, charts, data quality information, and campaign activity. |
| **Contact Data Lab** | Upload CSV/XLSX files, map columns, clean contact details, validate email syntax, identify duplicates, and export cleaned data. |
| **Designation Explorer** | Categorizes job titles using rules and lets you filter contacts by designation, company, and category. |
| **ML & NLP Intelligence** | Uses TF-IDF and Logistic Regression for title classification, with a rule-based fallback, model evaluation, keyword analysis, and explainable priority scores. |
| **Email Studio** | Creates email templates using `{Name}`, `{Company}`, and `{Title}` placeholders, previews personalized messages, and supports resume PDF attachments. |
| **Campaign Manager** | Supports simulated test campaigns and real email sending through Gmail SMTP, with recipient-level status tracking and a stop control. |
| **Campaign History & Reports** | Shows past campaigns, recipient statuses, filters, charts, review notes, and CSV/XLSX exports. |
| **Outreach Assistant** | Uses keyword-based commands to inspect data, summarize quality, suggest actions, and propose contact selections. It does not send emails itself. |

**ML evaluation note:** Classification metrics are based on synthetic labelled job titles. They should not be treated as real-world accuracy.

## Tech Stack

- **Language:** Python
- **UI:** Streamlit
- **Data processing:** Pandas, NumPy
- **Machine learning:** Scikit-learn, TF-IDF, Logistic Regression
- **Visualization:** Plotly
- **Email:** Gmail SMTP
- **Authentication:** bcrypt
- **Storage:** CSV, XLSX, and JSON files
- **Testing:** pytest with synthetic data and mocked SMTP

## Folder Structure

```text
outreach-iq/
├── app.py
├── requirements.txt
├── pytest.ini
├── .env.example
├── .gitignore
├── .streamlit/
│   └── config.toml
├── scripts/
│   ├── create_user.py
│   └── smtp_check.py
├── src/
│   └── outreachiq/
│       ├── config.py
│       ├── auth/
│       ├── data/
│       ├── ml/
│       ├── email_tools/
│       ├── campaigns/
│       ├── assistant/
│       └── ui/
├── sample_data/
├── tests/
├── data/       # Local data; gitignored
└── runtime/    # Local runtime files; gitignored
```

- `auth/` handles local login and authentication.
- `data/` contains contact loading, mapping, cleaning, validation, and export logic.
- `ml/` contains classification, evaluation, scoring, and NLP functionality.
- `email_tools/` handles templates, placeholders, attachments, and SMTP sending.
- `campaigns/` manages campaign history and reports.
- `assistant/` contains the keyword-based assistant workflow.
- `ui/` contains the Streamlit pages and shared interface components.

The structure above shows the main modules. Check the repository for the exact files currently included.

---

## Installation

Make sure Python is installed, then open a terminal in the project folder.

Create a virtual environment:

```powershell
python -m venv .venv
.venv\Scripts\Activate.ps1
```

Install the required packages:

```bash
pip install -r requirements.txt
```

## Local Login Setup

Create a local user:

```bash
python scripts/create_user.py
```

Choose a username and password when prompted. The password is stored as a bcrypt hash in `runtime/auth/credentials.json`, which should remain outside Git version control.

Start the app and log in using the credentials you created.

## Gmail Setup

Real email sending uses your Gmail account through an App Password, not your regular Gmail password.

1. Enable [2-Step Verification](https://myaccount.google.com/security) on your Google account.
2. Open your Google Account's Security settings and generate an App Password if your account is eligible.
3. Copy `.env.example` to `.env`.
4. Add your own configuration:

```dotenv
GMAIL_ADDRESS=your_address@gmail.com
GMAIL_APP_PASSWORD=your_16_char_app_password
SENDER_DISPLAY_NAME=Your Name
SMTP_HOST=smtp.gmail.com
SMTP_PORT=587
MAX_RECIPIENTS_PER_CAMPAIGN=100
SEND_DELAY_SECONDS=5
```

Use the exact variable names expected by your application's configuration. Never commit `.env` or share its contents.

### Check the SMTP connection

```bash
python scripts/smtp_check.py
```

This checks the SMTP connection without sending an email. The script prints `OK` or a failure stage with the exception class.

A successful connection test does not guarantee that an actual email will be delivered.

## Running the App

```bash
streamlit run app.py
```

Open the local URL shown in the terminal.

## Uploading and Cleaning Data

1. Open **Contact Data Lab**.
2. Upload a CSV or XLSX file.
3. Review the suggested column mapping and confirm it.
4. Clean and validate the mapped data.
5. Check invalid email syntax and duplicate records.
6. Export the cleaned data if needed.

The application is designed to save original uploads under `data/uploads/` and cleaned contacts under `data/processed/contacts_clean.csv`.

Sample datasets in `sample_data/` can be used to explore the workflow without uploading private contact information:

- `contacts_messy.csv`
- `contacts_alt_names.csv`
- `contacts_dirty.csv`

Email syntax validation does not confirm that an address exists or can receive messages.

## Designation Explorer

The rule-based categorization includes:

- HR / Recruiting
- Talent Acquisition
- Founder / CEO / Owner
- Director / Head
- Manager
- Other / Unknown

The rules are maintained in `src/outreachiq/data/designation.py` and can be adjusted for different datasets.

Selected contacts can be transferred to Email Studio for campaign preparation. Selecting contacts does not send emails.

## ML & NLP Intelligence

The title classifier uses TF-IDF features and Logistic Regression, with a rule-based fallback where appropriate.

Training and evaluation can use labelled titles from `sample_data/labelled_titles_synthetic.csv` or a suitable dataset provided by the user. The evaluation uses a stratified train/test split.

Priority scores range from 0–100 and include reasons explaining how the score was assigned. These scores are intended to help prioritize contacts; they are not predictions of hiring, replies, or email success.

**The reported classification metrics are based on synthetic labelled titles and do not establish real-world model performance.**

## Email Studio and Resume

Create a common email template using these placeholders:

- `{Name}`
- `{Company}`
- `{Title}`

The app fills these placeholders for each selected contact and uses fallback values when information is missing.

Upload a resume PDF through Email Studio. The documented maximum file size is 5 MB, and the file must have a valid `%PDF` signature. Resume files are stored under `runtime/resume/`.

Click **Prepare campaign** to generate personalized messages and check for unresolved placeholders.

Preparing a campaign does not send emails.

## Campaign Manager

### Test Mode

Test mode is the default. It simulates the sending workflow without sending emails or making SMTP network calls. Results are marked `Simulated`.

Use this mode to check recipient selection, message personalization, and campaign preparation.

### Real Send Mode

Real sending requires Gmail configuration, a prepared campaign, and explicit confirmation.

- Sends a separate email to each selected recipient.
- Supports a configurable delay between sends.
- Provides a stop control.
- Tracks recipient statuses such as `SMTP Accepted`, `Failed`, `Unknown/Needs Review`, and `Pending`.

Start with a small, approved test campaign before sending to a larger list. Follow Google's current sending limits and applicable privacy, consent, and anti-spam requirements.

**SMTP Accepted means Gmail's server accepted the message. It does not confirm inbox delivery.** Check your Gmail Sent folder when reviewing a send attempt.

For `Unknown/Needs Review`, the outcome may be uncertain. Check the campaign record and Gmail Sent folder before trying again, since an automatic retry could send a duplicate email.

## Campaign History & Reports

This page provides a read-only view of previous campaign records.

It supports:

- Filtering by date, mode, status, and search terms.
- Viewing campaign summaries and recipient-level statuses.
- Drilling down into individual campaigns.
- Charts for campaign activity and status distribution.
- Manual review notes for real-mode records marked Unknown/Needs Review.
- CSV/XLSX exports of filtered tables.

This page does not send emails or edit past campaign records. SMTP acceptance is not proof of delivery, opens, or replies.

## Outreach Assistant

The Outreach Assistant uses keyword matching rather than an LLM.

It can inspect available data, summarize data quality, suggest actions, and propose a contact selection for a campaign. After review, the selection can be transferred to the existing campaign workflow.

The assistant does not send emails itself. Review the selected contacts and prepared messages before approving a real campaign.

## Testing

Run the tests from the project root:

```bash
pytest
```

The test suite is intended to use synthetic data and mocked SMTP, so automated tests do not send real emails.

Use the actual output from your current test run when reporting the number of passing tests. Passing mocked tests does not verify real Gmail sending or inbox delivery.

## Limitations

- **SMTP acceptance is not delivery.** Gmail accepting a message does not guarantee that it reaches the recipient's inbox.
- **Gmail sending limits apply.** Limits depend on the account and Google's current policies. Large batches may be throttled, rejected, or flagged as spam.
- **File-based storage:** Campaign history, templates, models, and related runtime data are stored locally. This approach is simple but is not designed for high-concurrency use. The `HistoryStore` protocol in `campaigns/history_store.py` is intended to make a future move to SQLite easier.
- **Rule-based assistant:** The assistant uses keyword matching and cannot provide fully open-ended, LLM-style conversation.
- **Synthetic ML metrics:** Evaluation on synthetic titles does not establish real-world classification accuracy.
- **Email validation:** Syntax checks cannot confirm that an address is active or deliverable.
- **Local-first design:** This project is designed for personal local use, not as a hosted multi-user email service.

## Troubleshooting

| Problem | What to do |
|---|---|
| `SMTPServerDisconnected` at connect | Check your network, firewall, or VPN. Run `python scripts/smtp_check.py`. |
| SMTP authentication error | Check the configured email, confirm 2-Step Verification is enabled, and generate a new App Password if needed. |
| No resume found | Upload a PDF in Email Studio and check the file size and `%PDF` signature. |
| `Unknown/Needs Review` status | Check the campaign record and Gmail Sent folder before retrying. Avoid automatic retries that could create duplicate emails. |
| Page shows no data | Upload and clean contacts in Contact Data Lab, then check that the expected processed file exists. |
| Dependencies fail to install | Activate the virtual environment and check the Python version and dependency requirements. |
| Login credentials are missing | Run `python scripts/create_user.py` to create a local user. |

## Privacy & Security

- The application is designed to keep data on your local machine.
- `.env`, resume PDFs, real contact lists, campaign history, credentials, and private runtime files should remain outside version control.
- Passwords are bcrypt-hashed rather than stored in plaintext.
- Gmail App Passwords should never be committed, printed, or shared.
- Tests should use synthetic data and mocked SMTP, not real contact records or live email connections.
- Use `sample_data/` for public examples and demonstrations.
- Check `git status` and staged files before every commit or push.
- A private GitHub repository is not a substitute for secret management. If an App Password is exposed, revoke it and generate a replacement.

Before making this repository public, check both the tracked files and Git history for credentials, private resume documents, real contact lists, and private campaign records.

---

**Built by [Pranav Shrivastav](https://github.com/Pranav3536)**
