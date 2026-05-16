# AI Keyword Video Factory — Implementation Plan

**Companion to:** [ARCHITECTURE.md](./ARCHITECTURE.md)
**Date:** 2026-05-16

---

## 1. Implementation Phases

### Phase 1 — MVP Skeleton (target: 7–10 days)

**Goal:** end-to-end happy path for `output_count=1`, ONE working HTML template ("viral"), no real AI calls (mock LLM returns fixture script/scenes). Proves the Electron + sidecar + Chromium + FFmpeg toolchain works end-to-end.

- Electron + Vite + React + Tailwind shell.
- FastAPI sidecar boot from Electron main.
- Playwright lazy-installs Chromium on first run, cached in app data dir.
- Single-screen layout with all panels rendered.
- Folder picker via Electron dialog.
- One LangGraph run with mock adapters → fixture timeline (5 scenes).
- One HTML template ("viral") — kinetic typography on dark background + bg image.
- Playwright captures frames per scene; FFmpeg encodes to MP4.
- WebSocket pushes progress; UI renders pipeline + log + scene thumbnails.
- Video preview plays local file.
- Filename slug works for VI / EN / JA / KO / ZH inputs.

**Exit criteria:** click Generate with `keyword=karen` → 30s 9:16 MP4 with kinetic-typography motion + voice + burnt subtitles, file named `karen_viral_01.mp4`, previewable in-app.

### Phase 2 — Real AI Pipeline + More Templates (target: 10–14 days)

- Gemini adapter live (default); OpenAI + Claude adapters behind same interface.
- Language detection node wired to real LLM (or `langdetect`).
- Research, Idea, Script, Scene agents wired to real prompts in detected language.
- Pexels + Pixabay adapters (scene background images).
- Multi-variant fan-out for `output_count > 1` with concurrency cap.
- Idea cards UI populates from real LLM output.
- Subtitle ASS from edge-tts word timestamps.
- 5 more HTML templates: story, explainer, documentary, news, cinematic.
- Style picker drives both prompt AND template selection.
- Music bed mixed per style.

**Exit criteria:** input `karen / 9:16 / 70s / 5 / [viral,story,explainer]` → 5 distinct MP4s with different scripts, hooks, scenes, AND different visual styles per template.

### Phase 3 — Production Polish (target: 5–7 days)

- HW-accelerated encoding (NVENC / QSV / VideoToolbox auto-detect).
- Per-variant retry on stage failure.
- Compact log filtering, copy-to-clipboard, open log file.
- Re-render and Generate-Similar buttons.
- Crash recovery: scan `temp/` on startup, mark orphaned jobs errored.
- Voice picker (deferred from Phase 1).
- Signed installers for Win / Mac / Linux.

**Exit criteria:** signed installer; runs on fresh machine with no dev tools.

### Phase 4 — Premium (deferred, scoped)

- ElevenLabs voice adapter.
- AI image gen (Flux / DALL·E) for niche keywords without good stock matches.
- Remotion-based motion templates for advanced styles.
- Subtitle style picker (still no timeline editor).

---

## 2. Risks & Mitigations

| Risk | Impact | Mitigation |
|---|---|---|
| Chromium ~280MB inflates installer | install size, first-run delay | Playwright lazy-install on first launch with UI progress bar. NOT bundled in installer. |
| Frame capture slower than realtime on weak hardware | bad "Generate" UX | Show ETA prominently; Phase 3 draft mode (lower fps + CRF). |
| Non-deterministic CSS animations (timers, video tags) | frames out of sync | Template contract forbids `setTimeout`; CSS Web Animations only. Lint templates. |
| Missing fonts on user machine | wrong glyphs | Templates ship `@font-face` (Noto Sans + Noto Sans CJK). Never system fonts. |
| Disk pressure from PNG frames (~6GB / 70s) | render fails | Stream-encode each scene immediately; delete frame folder after. |
| Provider API rate limits during fan-out | partial job failure | Per-provider semaphore; exponential backoff; per-variant retry. |
| Stock asset returns junk for niche keywords | low video quality | Phase 2.5: score candidates via LLM; fallback to gradient + text-only scenes. |
| `output_count=10` runs out of disk | render fails | Pre-flight disk space check; refuse with clear error. |
| Sidecar port collision | app fails to start | Random port allocation; pass to renderer via preload. |
| Long-running jobs orphaned on app crash | stale temp files | Tag `temp/job_xxx/` with pid; sweep on startup. |
| Subtitle timing drift on long videos | unprofessional output | Drive timing from edge-tts word boundaries, not script estimates. |
| LangGraph state grows in memory | sidecar memory creep | Persist intermediate state to `temp/job_xxx/state.json`; refs only in memory. |
| Asset license compliance | legal | Log attribution per asset to `jobs.jsonl`. Phase 3: Credits view. |
| Electron + Python packaging on Windows | install pain | `pyinstaller --onedir`; bundle as `extraResources`. |
| Multi-lang script length variance | scenes don't fit duration | Script Agent prompted with target word count from per-language WPM tables (vi 150, en 160, ja 280 mora, ko 230, zh 180). |

---

## 3. Verification & Test Checklist

For each phase, do not claim done without:

**Backend**
- `pytest` green on adapter contracts (mocked providers).
- Timeline JSON round-trip test (Pydantic → renderer → output exists).
- WS event order test: simulate job, assert event sequence matches contract.
- Disk usage test: 5-variant job leaves no leftover `temp/`.
- Slug test: VI / EN / JA / KO / ZH keyword inputs → filesystem-safe filenames.

**Frontend**
- Vitest unit tests for `applyEvent` reducer (every event type maps cleanly).
- Storybook stories per component: empty, loading, error.
- Lighthouse desktop perf ≥ 90.
- Keyboard navigation: every input reachable via Tab.

**Render correctness**
- Golden-frame test: render fixture timeline, diff first / last / middle frames vs checked-in PNGs (with AA tolerance).
- Audio sync test: render fixture, verify voice + subtitle on-screen at expected timestamps.

**End-to-end**
- Playwright on Electron: launch app, fill setup, click Generate, assert MP4 exists at expected slugified path within timeout.
- Resize window 1280×800 → 1920×1080: no overlap, no clipping.

**Production**
- Signed Win installer runs on clean VM, no dev tools.
- App quit kills sidecar (no zombie Python).
- Logs rotated at 10MB.

---

## 4. Locked Decisions (2026-05-16)

| # | Question | Decision |
|---|---|---|
| 1 | Render engine | **HTML Scene + Playwright + FFmpeg encode** |
| 2 | State persistence | **Fully stateless** (no project history) |
| 3 | Scene editing | **None** — fully automated, no Edit buttons |
| 4 | Input mode | **Keyword-only** |
| 5 | Default LLM provider | **Gemini** (adapter pattern keeps OpenAI/Claude swappable) |
| 6 | Phase 1 template | **Viral** (kinetic typography on dark background) |
| 7 | Language | **Multi-language auto-detect** (VI / EN / JA / KO / ZH / …) |
| 8 | Output naming | `<keyword_slug>_<style>_<NN>.mp4` (slug rules in ARCHITECTURE §7) |
| 9 | Music beds | **Ship 6 royalty-free tracks** (one per style) |
| 10 | edge-tts voice | Single default per language; voice picker deferred to Phase 3 |
| 11 | Min window size | 1280×800 |
| 12 | Watermark / telemetry | Deferred to business-model discussion; off by default in v1 |

**Status: ready to scaffold Phase 1.**

---

## 5. Next Steps

I'll execute Phase 1 in 4 steps, pausing after each for your review:

1. **Repo scaffold** — folder structure, root `package.json`, `pyproject.toml`, `.gitignore`, `README.md`, lint configs. No business logic.
2. **Electron + FastAPI handshake** — app launches, sidecar boots, UI calls `/api/health`, gets 200. Proves the toolchain.
3. **Single-screen UI shell** — all panels rendered with mock data, no real interactivity beyond input.
4. **Mock pipeline + viral template + render** — fixture LangGraph + one HTML "viral" template + Playwright capture + FFmpeg encode end-to-end.

After Phase 1 exits cleanly, Phase 2 wires the real AI.

---

**Files reviewed:** spec text (user); 12 demo video frames.
**Files written:** `ARCHITECTURE.md`, `PLAN.md`, `reference-frames/*.jpg`.
**Changes to existing code:** none.
**Risks documented:** 15 in §2 above.
**Verification plan:** §3 above.
