# 📄 Research Paper Digest Agent

An AI agent that discovers trending research papers in your chosen domains, ranks them, picks the best one per day, breaks its abstract down with an LLM, and emails you a clean summary — fully automated via GitHub Actions.

## How It Works

```
config/users.yaml ──► multi-source discovery ──► rank & select ──► LLM breakdown (OpenRouter)
        (arXiv 25/domain + HF trending + bioRxiv)         │
email (Gmail SMTP) ◄── render HTML email ◄─────────────────┘
        │
        └──► data/history.json (auto-pruned after 730 days, never repeat within 2 years)
```

## Two tracks

A paper submitted today has zero citations, so impact and newsworthiness are pulled in
opposite directions. The digest runs both and alternates:

| Track | When | Candidates | Ranked by |
|-------|------|------------|-----------|
| **Fresh** | 4 out of 5 sends | last 7 days from your sources | keywords, recency, category, upvotes, citations |
| **Established** | every 5th send | Semantic Scholar top-cited from the last 3 months, per domain query | citation count |

The cadence counts that email's own sends, so it survives across cron runs via the committed
history. Tune with `ESTABLISHED_EVERY_NTH_SEND`, `ESTABLISHED_MONTHS` and
`ESTABLISHED_PER_DOMAIN` in `src/config_loader.py`. Set the cadence to `0` to disable the
established track.

Why the established track uses Semantic Scholar search instead of an older arXiv window: a
12-month arXiv sample topped out at 32 citations (only 2 papers above 10), because arXiv-only
preprints are rarely cited. Semantic Scholar's citation-sorted search returns real signal.

Note that a 3-month window caps how much impact a paper can have accumulated — the current
leader is around 90 citations, versus ~22,000 for the same query over 3 years. Widen
`ESTABLISHED_MONTHS` if you want landmark-scale papers rather than the hottest recent ones.

## Project Structure

```
├── config/users.yaml            # users, emails, domains & keywords
├── src/
│   ├── config_loader.py         # config + env vars
│   ├── discovery.py             # source fan-out + relevance scoring
│   ├── sources/
│   │   ├── arxiv_source.py      # arXiv API search
│   │   ├── hf_source.py         # Hugging Face daily papers (community upvotes)
│   │   ├── biorxiv_source.py    # bioRxiv / medRxiv recent preprints
│   │   ├── scholar.py           # Semantic Scholar: citation counts + top-cited search
│   │   ├── base.py              # Paper model shared by all sources
│   │   └── http.py              # retrying JSON requests
│   ├── selection.py             # pick best un-sent paper + history pruning
│   ├── analyzer.py              # abstract-only OpenRouter breakdown w/ model fallback
│   ├── emailer.py               # HTML email via Gmail SMTP
│   └── main.py                  # orchestrator (run: python -m src.main)
├── .github/workflows/daily.yml  # daily cron at 03:00 UTC
├── data/history.json            # created automatically after first send
└── requirements.txt
```

## Sources

Set `sources` per domain in `config/users.yaml` (default: `arxiv`):

- `arxiv` — arXiv API, 25 newest matching the domain's `categories` + `query`
- `huggingface` — HF daily papers; community `upvotes` feed the ranking
- `biorxiv` / `medrxiv` — recent preprints (DOI-keyed, JATS markup stripped)

Non-arXiv sources have no category filter, so a paper is only kept for a domain when it
mentions one of that domain's `keywords` (at least 1 hit). Duplicates across sources are
merged by paper id, preferring the arXiv record.

## Ranking

Each candidate paper is scored in `src/discovery.py`:

```
score = keyword_hits * KEYWORD_WEIGHT (2.0)
      + recency_score * RECENCY_WEIGHT (3.0)      # decays to 0 over 30 days
      + category_bonus (1.5)                      # primary category matches the domain
      + citation_score * CITATION_WEIGHT (3.0)    # log10(100 citations) = full credit
      + upvote_score * UPVOTE_WEIGHT (1.5)        # HF community upvotes
```

The highest-scoring paper that has not been sent in the last 730 days wins. All weights live
at the top of `src/discovery.py` — change them to change what "best" means. Ties are broken by
the order domains appear in `config/users.yaml`.

Note that on the fresh track the citation term contributes close to nothing, because the pool is
only a week old and Semantic Scholar has not indexed those papers yet. That is expected: it
earns its weight on the established track.

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
- Default models are `nvidia/nemotron-3-ultra-550b-a55b:free` with `nvidia/nemotron-3-super-120b-a12b:free` as fallback. Reasoning is enabled on each request (`"reasoning": {"enabled": true}`). Free model IDs disappear often — list the current ones at https://openrouter.ai/models and set `OPENROUTER_MODEL_1` / `OPENROUTER_MODEL_2` if the defaults stop working.
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
        sources: [arxiv, huggingface]
        categories: [cs.LG]
        keywords: [RLHF, reward model, policy optimization]
```

- `query`: arXiv full-text search terms
- `categories`: arXiv category filters (cs.CL, cs.CV, cs.LG, q-bio.QC, ...)
- `keywords`: boost papers mentioning these terms
- `sources`: which feeds to search (see [Sources](#sources))

Add more users under `users:` and each gets their own daily paper.

## Notes

- Only the **abstract** is sent to the LLM (no PDF download), which keeps runs fast and free.
- The digest has two sections: **In Simple Terms** and **Why It Matters & Future Uses**.
- Free OpenRouter models occasionally rate-limit; the agent automatically falls back to a second model, and if both fail it sends the raw abstract instead of failing silently.
- Sent history is committed back to the repo, and entries older than 730 days are dropped on
  startup (`HISTORY_MAX_AGE_DAYS` in `src/config_loader.py`). The cooldown matters because the
  established track can keep resurfacing the same paper - with a 7-day cooldown you would be
  emailed the same hit every week.
- Any single source failing (rate limit, outage) is logged and skipped; the run continues on
  the remaining sources.
- Citation counts come from Semantic Scholar's free tier. Set `SEMANTIC_SCHOLAR_API_KEY` in
  `.env` for higher rate limits, or `CITATIONS_ENABLED=false` to turn the lookup off.
