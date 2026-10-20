# OutreachIQ Project Steering

- Read TASKS.md and PROJECT_STATE.md first; edit only files needed for the current task.
- Stack: Python, Streamlit, pandas, scikit-learn, smtplib only. No paid APIs, no DB, no LLM APIs.
- Never commit or print secrets. .env, resume PDF, contact CSV/XLSX, campaign history stay gitignored.
- Never ask the user to paste credentials in chat; credentials live only in local .env.
- Tests/samples use synthetic data only. Never fake results or mark a task done without passing tests.
- Email: one separate email per recipient, never auto-send, no unresolved {placeholders}, never auto-retry ambiguous SMTP failures. SMTP accepted is not inbox delivered.
- After each task: update TASKS.md and PROJECT_STATE.md briefly, then give a handoff of max 10 lines with the next task.
- Work in small steps; log each finished module in TASKS.md before moving on.
- Run only task-related tests unless told "full test". No code in replies. Final reply max 5 lines.
- Prefer small edits over rewrites.
