# AI Keyword Video Factory

Desktop application that turns a single keyword into multiple finished MP4 videos, fully automated by AI.

Input: keyword + format + duration + count + styles + output folder.
Output: N distinct MP4s, each with its own script, scenes, voice, and burnt subtitles.

This is NOT a video editor. Stateless. Local-first. Single screen.

See [ARCHITECTURE.md](./ARCHITECTURE.md) and [PLAN.md](./PLAN.md) for the full design.

---

## Repo Layout

```
apps/desktop/       Electron + React + Vite UI
backend/            FastAPI sidecar + LangGraph agents + Playwright/FFmpeg renderer
assets/             Bundled fonts (Noto Sans + CJK) and music beds
docs/               Additional design docs
logs/               Runtime logs (gitignored)
temp/               Render scratch dirs (gitignored)
reference-frames/   Frames extracted from the demo video (design reference, local only)
```

---

## Prerequisites

- Node.js **20.11.1** (see `.nvmrc`)
- Python **3.11.9** (see `.python-version`)
- FFmpeg in PATH (bundled at install time for end users)
- Playwright will install its own Chromium on first run

---

## Dev Setup (Phase 1 — coming next step)

```bash
# Desktop app
cd apps/desktop
npm install
npm run dev          # launches Electron with HMR + spawns sidecar

# Backend (standalone, for testing without Electron)
cd backend
python -m venv .venv
. .venv/bin/activate     # Windows: .venv\Scripts\activate
pip install -e .
python -m playwright install chromium
uvicorn app.main:app --reload --port 8000
```

Detailed scripts will be wired up in Step 2 (Electron + FastAPI handshake).

---

## Status

Currently at: **Phase 1, Step 1 — Repo scaffold (no code logic yet).**

See [PLAN.md §1](./PLAN.md) for the full phase breakdown.
