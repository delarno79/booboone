# Booboone Auto-Blog

An autonomous content engine. It pulls unused keywords from your keyword list,
writes a unique SEO article for each with **DeepSeek**, generates a matching
featured image with **Google Gemini/Imagen**, and publishes the post straight to
your **WordPress** site — one post per category, on a schedule, with zero manual
work. Every keyword is tracked so the same article is never written twice.

```
keywords.json ──▶ DeepSeek (article) ──▶ Gemini (featured image)
                                             │
                                             ▼
                              WordPress REST API (publish post)
                                             │
                                             ▼
                       keywords.state.json (marks keyword as used)
```

---

## 1. Install

Requires Python 3.10+.

```bash
pip install -r requirements.txt
```

## 2. Configure (you can change these any time)

Copy the template and fill in your keys and site details:

```bash
cp .env.example .env
```

| Setting | What it is |
|---|---|
| `WP_URL` | Your site, e.g. `https://booboone.com` |
| `WP_USER` | Your WordPress username |
| `WP_APP_PASSWORD` | An **Application Password** (see below) — not your login password |
| `DEEPSEEK_API_KEY` | Your DeepSeek key (writes the articles) |
| `GEMINI_API_KEY` | Your Google Gemini key (makes the images) |
| `POST_STATUS` | `publish` (go live) or `draft` (review first) |
| `GENERATE_IMAGES` | `true` or `false` |
| `MAX_POSTS_PER_RUN` | Optional cap; blank = one per category |

**Getting a WordPress Application Password:** WP Admin → **Users → Profile** →
scroll to **Application Passwords** → enter a name → **Add New**. Copy the
generated password (with spaces) into `WP_APP_PASSWORD`.

## 3. Load your keywords

Convert the client's Word document into `keywords.json`:

```bash
python convert_docx.py "Booboone Keyword List.docx"
```

It prints a summary of the detected categories and keywords. Review
`keywords.json` and fix by hand if anything looks off — the format is simple:

```json
{
  "Business & Finance": ["small business bank account", "business line of credit"],
  "Beauty & Fashion":   ["eye creams for dark circles"]
}
```

> No document yet? Copy `keywords.sample.json` to `keywords.json` to try it out.

## 4. Verify everything

```bash
python setup_check.py
```

This confirms your `.env`, the keyword file, WordPress login, and DeepSeek key
all work **before** you publish anything.

## 5. Run

```bash
python main.py --dry-run     # writes articles, publishes nothing (safe test)
python main.py               # one article per category, published for real
python main.py --status      # how many keywords remain per category
python main.py --limit 3     # only publish 3 this run
python main.py --category "Beauty & Fashion"
```

Categories are matched to your WordPress categories automatically — and any that
don't exist yet are created for you.

---

## 6. Run it automatically (the "set and forget" part)

### Option A — GitHub Actions (free, recommended)

1. Push this project to a **private** GitHub repo.
2. Repo → **Settings → Secrets and variables → Actions** → add secrets:
   `WP_URL`, `WP_USER`, `WP_APP_PASSWORD`, `DEEPSEEK_API_KEY`, `GEMINI_API_KEY`.
3. The included workflow (`.github/workflows/publish.yml`) already runs 3×/day
   (08:00, 14:00, 20:00 UTC) and commits progress back so nothing repeats.
   Change the times by editing the `cron` line.

### Option B — PythonAnywhere / any server (cron)

Add a scheduled task running `python main.py`. Example crontab for 3×/day:

```
0 8,14,20 * * *  cd /path/to/project && python main.py >> logs/cron.log 2>&1
```

---

## Notes & troubleshooting

- **Nothing repeats:** used keywords are recorded in `keywords.state.json`. Delete
  an entry there to allow a keyword to be reused.
- **Featured images:** by default (`IMAGE_SOURCE=free_ai`) the bot generates a
  unique **AI image for free** via Pollinations, with a free stock photo as
  fallback — no Google billing needed. Google's own Gemini/Imagen image API is
  **paid-only** (free tier has zero image quota), so only use `IMAGE_SOURCE=ai`
  or `auto` if the client has enabled billing. Set `GENERATE_IMAGES=false` to
  skip images entirely.
- **Logs:** every run writes to `logs/autoblog-YYYY-MM-DD.log`.
- **Safety:** start with `POST_STATUS=draft` to review the first batch, then switch
  to `publish` once you're happy with the quality.
