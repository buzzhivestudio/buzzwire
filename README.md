# BuzzWire

BuzzWire is a local MVP for turning raw news and trending topics into page-specific Instagram content angles. It supports page profiles, RSS/manual topic intake, classification, page matching, viral title/caption generation, and a human approval board.

## What Works

- FastAPI backend with SQLite storage locally and Supabase/Postgres in production
- Config-driven page profiles and RSS sources
- RSS fetch layer with `feedparser`
- Manual topic input
- Topic classification with categories, country relevance, emotional triggers, virality, and risk
- Page matching against allowed/blocked topics, emotional drivers, and risk tolerance
- Rule-based viral angle generation plus optional OpenAI, Claude, or Gemini generation
- Local approval dashboard with page filters, good-ideas-only filter, editing, approval, rejection, regeneration, and tone changes
- JSON and Markdown exports
- Provider abstraction for future OpenAI, Claude, or Gemini integrations

## Setup

```powershell
python -m venv .venv
.\.venv\Scripts\Activate.ps1
pip install -r requirements.txt
uvicorn buzzwire.main:app --reload
```

Then open [http://127.0.0.1:8000](http://127.0.0.1:8000).

If your machine does not expose `python`, use the Codex bundled Python path shown by the workspace runtime.

## Data

SQLite is stored at `data/buzzwire.db` by default. If `DATABASE_URL` starts with `postgres://` or `postgresql://`, BuzzWire uses Postgres instead. On startup, the app creates missing tables and seeds:

- `config/page_profiles.json`
- `config/rss_feeds.json`

Edit those files to add more Instagram page profiles or RSS sources.

## Private Access

Set both auth variables to require one username and password for the whole dashboard and API:

```powershell
BUZZWIRE_AUTH_USERNAME=your-username
BUZZWIRE_AUTH_PASSWORD=your-strong-password
```

Leave them blank for open local development. `/api/health` stays public so hosting platforms can run health checks.

## Vercel + Supabase

For the cheap internal setup, use Vercel for the app and Supabase for the database.

1. Create a Supabase project.
2. Copy the Supabase Postgres connection string. For serverless hosting, the Supabase pooler URL is preferred.
3. Create/import the project on Vercel.
4. Add these Vercel environment variables:

```bash
DATABASE_URL=postgresql://...
BUZZWIRE_AUTH_USERNAME=your-username
BUZZWIRE_AUTH_PASSWORD=your-strong-password
BUZZWIRE_MODEL_PROVIDER=rule_based
```

The app protects the dashboard and API with the BuzzWire username/password. `/api/health` stays public for checks.

Vercel uses `api/index.py` as the FastAPI entrypoint and `vercel.json` routes all traffic to it.

## Other Hosting Notes

For a normal VPS or platform with a persistent disk, SQLite is still fine.

Start command:

```bash
uvicorn buzzwire.main:app --host 0.0.0.0 --port $PORT
```

Recommended SQLite production env:

```bash
BUZZWIRE_DB=/data/buzzwire.db
BUZZWIRE_AUTH_USERNAME=your-username
BUZZWIRE_AUTH_PASSWORD=your-strong-password
BUZZWIRE_MODEL_PROVIDER=auto
```

Mount the persistent disk or volume at `/data` so the board survives redeploys.

## API Highlights

- `POST /api/manual-topic` adds one manual topic and runs the pipeline
- `POST /api/fetch/rss` fetches enabled RSS feeds and runs the pipeline
- `GET /api/board` returns board columns
- `POST /api/posts/{id}/approve`
- `POST /api/posts/{id}/reject`
- `POST /api/posts/{id}/regenerate-title`
- `POST /api/posts/{id}/regenerate-caption`
- `POST /api/posts/{id}/change-tone`
- `POST /api/posts/{id}/edit`
- `GET /api/provider`
- `GET /api/export/json`
- `GET /api/export/markdown`

## Instagram Training Lab

Use `scripts/instagram_training_lab.py` to turn public reference posts into private pattern analysis for BuzzWire. Keep downloaded media in `data/training/`, which is ignored by Git.

Create a CSV with:

```csv
post_url,likes,views,hook_text,caption,frame_path,media_path
https://www.instagram.com/p/...,871K,54.9M,Unlocking a number lock should not be this easy,,
```

Run analysis only:

```powershell
.\.venv\Scripts\python.exe scripts\instagram_training_lab.py data\training\wealth_posts.csv --out data\training\wealth --sort-by views
```

Run with local download/frame extraction when you have permission to use the posts as private reference material:

```powershell
.\.venv\Scripts\python.exe -m pip install yt-dlp
.\.venv\Scripts\python.exe scripts\instagram_training_lab.py data\training\wealth_posts.csv --out data\training\wealth --sort-by views --download --cookies-browser chrome
```

For Instagram photo or carousel batches where true views are not visible, use `--sort-by likes`.

Outputs:

- `contact_sheet_by_views.html` or `contact_sheet_by_likes.html`
- `training_summary.md`
- `pattern_analysis.json`
- `training_examples.json`

## Provider Layer

`BUZZWIRE_MODEL_PROVIDER=rule_based` is the working default and needs no API key.

To use a real model provider, copy `.env.example` to `.env`, add one or more keys, and set:

```powershell
BUZZWIRE_MODEL_PROVIDER=auto
```

`auto` checks keys in this order: OpenAI, Anthropic, Gemini. You can also set `BUZZWIRE_MODEL_PROVIDER=openai`, `anthropic`, or `gemini` directly.

Optional model overrides:

- `OPENAI_MODEL=gpt-5`
- `ANTHROPIC_MODEL=claude-sonnet-4-20250514`
- `GEMINI_MODEL=gemini-2.5-flash`

By default, `BUZZWIRE_FALLBACK_TO_RULE_BASED=true`, so quota/rate/API errors do not break the approval workflow. Failed live generations fall back to the local engine and add a note to the post's safety notes.
