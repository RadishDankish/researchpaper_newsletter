# 📄 Research Paper Digest Agent

An AI agent that discovers trending research papers in your chosen domains, picks one per day, breaks it down with an LLM, and emails you a clean summary — fully automated via GitHub Actions.

## How It Works

```
config/users.yaml ──► arXiv discovery ──► rank & select ──► download PDF ──► extract text
                                                                            │
email (Gmail SMTP) ◄── render HTML email ◄── LLM breakdown (OpenRouter) ◄───┘
        │
        └──► data/history.json (never repeat a paper)
```

## Project Structure

```
├── config/users.yaml            # users, emails, domains & keywords
├── src/
│   ├── config_loader.py         # config + env vars
│   ├── discovery.py             # arXiv search + relevance scoring
│   ├── selection.py             # pick best un-sent paper
│   ├── extraction.py            # PDF download + text extraction
│   ├── analyzer.py              # OpenRouter breakdown w/ model fallback
│   ├── emailer.py               # HTML email via Gmail SMTP
│   ├── history.py               # sent-paper tracking
│   └── main.py                  # orchestrator (run: python -m src.main)
├── .github/workflows/daily.yml  # daily cron at 03:00 UTC
├── data/history.json            # created automatically after first send
└── requirements.txt
```

## Setup

### 1. Local setup

```powershell
pip install -r requirements.txt
copy .env.example .env    # then fill in your keys
python -m src.main --dry-run   # preview without sending email or needing keys
python -m src.main             # real run
```

### 2. Get your credentials

- **OpenRouter key**: create at https://openrouter.ai/keys (free models used by default)
- **Gmail App Password**: enable 2FA on your Google account, then create an app password at https://myaccount.google.com/apppasswords (16 characters)

### 3. GitHub Actions automation

1. Push this repo to GitHub
2. Add repository **Secrets** (Settings → Secrets and variables → Actions):
   - `OPENROUTER_API_KEY`
   - `GMAIL_ADDRESS`
   - `GMAIL_APP_PASSWORD`
   - Optional: `OPENROUTER_MODEL_1`, `OPENROUTER_MODEL_2` to override free models
3. The workflow runs daily at **03:00 UTC** (edit the `cron` line in `.github/workflows/daily.yml` for a different time)
4. You can also trigger it manually from the Actions tab ("Run workflow")

## Customizing Domains

Edit `config/users.yaml`. Each user can have any number of domains:

```yaml
users:
  - name: Danish
    email: you@gmail.com
    domains:
      - name: Reinforcement Learning
        query: "reinforcement learning"
        categories: [cs.LG]
        keywords: [RLHF, reward model, policy optimization]
```

- `query`: arXiv full-text search terms
- `categories`: arXiv category filters (cs.CL, cs.CV, cs.LG, q-bio.QC, ...)
- `keywords`: boost papers mentioning these terms

Add more users under `users:` and each gets their own daily paper.

## Notes

- Free OpenRouter models occasionally rate-limit; the agent automatically falls back to a second model, and if both fail it sends the raw abstract instead of failing silently.
- Sent history is committed back to the repo so repeats are avoided across runs.
