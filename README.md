# Fetchly — Universal Video Downloader

A production-ready video downloader supporting YouTube, TikTok, Instagram,
X/Twitter, Facebook, Reddit, Vimeo, Twitch, Dailymotion, Pinterest,
LinkedIn, and Streamable — plus anything else yt-dlp's extractor library
covers, if you choose to widen the allowlist.

## Architecture

Two independently deployed services:

```
┌─────────────────┐         ┌──────────────────────┐
│  Next.js 15      │  HTTPS  │  FastAPI + yt-dlp     │
│  (Vercel)        │ ──────▶ │  (Render)             │
│                  │ ◀────── │                       │
│  - URL input     │  SSE    │  - metadata extraction│
│  - format list   │         │  - download + merge   │
│  - progress UI   │         │  - SSRF-safe fetching │
└─────────────────┘         └──────────────────────┘
```

**Why two services instead of one Next.js app with API routes:** yt-dlp
needs a real, long-running process with disk access and an `ffmpeg`
binary to merge separate audio/video streams. That's fundamentally
incompatible with Vercel's serverless functions (execution time limits,
no persistent filesystem, no bundled ffmpeg). The backend needs a real
container host; the frontend doesn't.

### Request flow

1. **`POST /api/metadata`** — validates the URL against a domain
   allowlist, resolves the hostname and rejects anything pointing at a
   private/internal IP (SSRF protection — see `backend/app/services/security.py`),
   then runs yt-dlp with `skip_download=True` to pull title, thumbnail,
   duration, and every available format. Formats are deduplicated and
   sorted highest-quality-first server-side.
2. Frontend renders the format list. Each row has its own independent
   download button and progress state.
3. **`POST /api/download`** — creates a job, kicks off a background task
   that runs the actual yt-dlp download (in a thread pool, so it doesn't
   block the event loop) and returns a `job_id` immediately.
4. **`GET /api/progress/{job_id}`** — Server-Sent Events stream. The
   frontend subscribes with a native `EventSource` and updates the
   progress bar, speed, and ETA live.
5. On completion, the frontend triggers a browser download from
   **`GET /api/file/{job_id}`**, which streams the file with a sanitized
   filename and proper `Content-Disposition` header.
6. A background sweeper deletes job directories after 30 minutes
   (configurable), whether or not the client picked up the file.

### Security model

- **Domain allowlist** — only known video-platform URLs are accepted;
  everything else is rejected before it reaches yt-dlp
- **DNS-rebinding protection** — the resolved IP is checked against
  private/loopback/link-local ranges, not just the hostname string
- **Restricted extractors** — yt-dlp's `allowed_extractors` option is
  set explicitly, so its generic/fallback extractor (which will attempt
  to scrape *any* URL) never runs
- **Rate limiting** — sliding-window limiter per IP on all `/api/*` routes
- **Concurrency caps** — per-IP and global limits on simultaneous
  downloads, plus a max video duration, to bound resource usage
- **Filename sanitization** — strips path separators and control
  characters before anything touches the filesystem or an HTTP header
- Full test coverage for all of the above in `backend/tests/test_security.py`

---

## Installation & Setup

### Prerequisites
- Node.js 18.18+ (frontend)
- Python 3.12+ (backend)
- `ffmpeg` installed locally if running the backend outside Docker
  (`brew install ffmpeg` / `apt install ffmpeg`) — required for merging
  separate audio/video streams into one file

### Backend
```bash
cd backend
python3 -m venv venv
source venv/bin/activate        # Windows: venv\Scripts\activate
pip install -r requirements.txt
cp .env.example .env
uvicorn app.main:app --reload --port 8000
```
API docs are auto-generated at `http://localhost:8000/docs`.

**Or via Docker** (includes ffmpeg, no local Python setup needed):
```bash
docker compose up --build
```

### Frontend
```bash
cd frontend
npm install
cp .env.local.example .env.local   # points at localhost:8000 by default
npm run dev
```
Open `http://localhost:3000`.

---

## Development Workflow

- Backend tests: `cd backend && pytest tests/ -v`
- Frontend type-check: `cd frontend && npx tsc --noEmit`
- Both services hot-reload on save in dev mode

Adding a new platform: add its domain(s) to `ALLOWED_DOMAINS` in
`backend/app/services/security.py` and its yt-dlp extractor name to
`allowed_extractors` in `backend/app/config.py`. Check yt-dlp's
extractor name with `yt-dlp --list-extractors | grep -i <platform>`.

---

## Environment Configuration

**Backend** (`backend/.env`, see `.env.example` for full list):
| Variable | Purpose |
|---|---|
| `CORS_ORIGINS` | Comma-separated frontend origins allowed to call the API |
| `MAX_VIDEO_DURATION_SECONDS` | Reject videos longer than this |
| `MAX_CONCURRENT_JOBS_PER_IP` | Per-visitor concurrent download cap |
| `RATE_LIMIT_REQUESTS_PER_MINUTE` | API rate limit per IP |

**Frontend** (`frontend/.env.local`):
| Variable | Purpose |
|---|---|
| `NEXT_PUBLIC_API_URL` | Base URL of the deployed backend |

---

## Build Instructions

**Backend:** `docker build -t fetchly-backend ./backend`
**Frontend:** `cd frontend && npm run build`

---

## Deployment Guide

### Backend → Render (free, no credit card required)
Render offers a genuinely free Docker-native web service tier — no card
needed to start. The only tradeoff: free services sleep after 15 minutes
of inactivity and take 30-60 seconds to wake up on the next request.
That's a fair trade for $0/month on a personal project.

*(Railway and Fly.io both removed their free tiers in 2024 and now
require a credit card from day one, roughly $5/month minimum even for
a small always-on service — only go that route if you specifically want
to avoid cold starts and don't mind the cost.)*

1. Push this repo to GitHub
2. Render dashboard → New → Web Service → connect your GitHub repo
3. Set **Root Directory** to `backend` — Render auto-detects the
   Dockerfile from there
4. Add the environment variables from `.env.example` under the
   service's Environment tab, setting `CORS_ORIGINS` to your actual
   Vercel domain once you have it
5. Deploy. Render gives you a public URL like
   `fetchly-backend.onrender.com`

### Frontend → Vercel
1. Vercel → New Project → import this repo → set root directory to `/frontend`
2. Add environment variable `NEXT_PUBLIC_API_URL` = your Render backend URL
3. Deploy

### Important production checklist
- [ ] Set `CORS_ORIGINS` on the backend to your real frontend domain (not `*`)
- [ ] Confirm `ffmpeg` is present in the deployed container (it's in the Dockerfile — don't switch to a buildpack that skips it)
- [ ] Consider moving `JobManager` and the rate limiter from in-memory to Redis if you ever run more than one backend replica (see docstrings in `job_manager.py` and `rate_limit.py` — they're written as a single seam to swap)
- [ ] Watch disk usage on the backend host — temp files are swept every 30 min by default, tune `JOB_TTL_SECONDS` down if you're tight on storage
- [ ] If the free tier's cold starts become annoying, Render's paid Starter tier ($7/mo) removes sleep entirely — no code changes needed to upgrade

---

## Troubleshooting

**"This URL could not be processed"** — the domain isn't in the
allowlist, or it resolved to a private IP. Check `ALLOWED_DOMAINS` in
`security.py`.

**Downloads stuck at "merging"** — `ffmpeg` isn't installed/found on the
backend host. Confirm with `ffmpeg -version` inside the container.

**CORS errors in the browser console** — `CORS_ORIGINS` on the backend
doesn't include your frontend's actual origin (protocol + domain must
match exactly, including `https://`).

**SSE progress never updates** — some reverse proxies buffer streaming
responses by default. If you put anything in front of the FastAPI
backend (nginx, Cloudflare in "proxied" mode, etc.), disable buffering
for the `/api/progress/*` route.

**"This video requires sign-in and can't be fetched" on YouTube links
that work fine in a real browser** — this is YouTube's bot detection
flagging your server's IP, not an issue with the video itself. Cloud
hosts (Render, Railway, AWS, etc.) get hit with this far more than
residential IPs. The app already mitigates it by trying yt-dlp's
android/ios player clients before falling back to web (see
`_base_ydl_opts()` in `ytdlp_service.py`), which resolves it for most
videos. If a specific video still fails:
1. Confirm yt-dlp is up to date — `pip install -U yt-dlp` and redeploy.
   This is a genuine cat-and-mouse game between YouTube and yt-dlp;
   new releases ship patches for this frequently.
2. As a last resort, export cookies from a real logged-in YouTube
   session (a browser extension like "Get cookies.txt LOCALLY" makes
   this easy), upload the file to your backend host, and point
   `COOKIES_FILE` at it. Be aware this ties the download service to
   that specific Google account's session — treat it as a stopgap, not
   a permanent fix, and don't use an account you care about, since
   heavy automated use can get it flagged.
3. At real scale, a residential proxy service becomes the reliable fix
   — datacenter IP reputation is the root cause and nothing server-side
   fully eliminates it. Not necessary for personal/low-traffic use.

**A specific video fails but works on the platform directly** — yt-dlp
updates frequently to keep up with platform changes. Try
`pip install -U yt-dlp` and redeploy.

---

## Legal

This tool downloads publicly accessible content using an open-source
extraction library. It doesn't host, store, or redistribute anything —
files are streamed directly to the person who requested them and
deleted shortly after. Respect the terms of service of the platforms
you use this with, and only download content you have the right to.
