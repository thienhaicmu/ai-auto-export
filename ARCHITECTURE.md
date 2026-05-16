# AI Keyword Video Factory — Architecture

**Version:** 0.3 (all decisions resolved — ready for Phase 1 scaffold)
**Date:** 2026-05-16
**Status:** Approved for implementation — no code written yet
**Companion docs:** [PLAN.md](./PLAN.md) — phases, risks, verification, decisions, next steps.

---

## 1. Executive Summary

A desktop application that turns a single keyword into multiple finished MP4 videos, fully automated by AI. User picks keyword → idea → format/duration/count/styles → output folder → clicks Generate. AI handles research, scripting, scene composition, voice, subtitles, asset sourcing, and render. Videos land directly in the user's chosen folder and preview inside the app.

**This is NOT a video editor.** No timeline editing. No project management. No cloud upload. Stateless. Local-first. Single screen.

---

## 2. Spec Audit — Key Constraints

- **Single screen** — no router, no wizard. React + Zustand stores only.
- **Stateless** — no DB, no project manager. `logs/`, `temp/`, `output/` only.
- **Local-first** — Electron + Python sidecar + FFmpeg + Chromium. No cloud.
- **Automation-first** — AI does the work. UI shows progress, not controls. No scene editing.
- **Multiple distinct videos per run** — each output gets its own script, scenes, hook, pacing.
- **Dark premium AI-creator aesthetic** — Runway / CapCut Desktop / Linear / Arc vibe.
- **Adapter-based providers** — Gemini default; OpenAI / Claude swappable. edge-tts default; ElevenLabs / Piper swappable.
- **Multi-language auto-detect** — VI / EN / JA / KO / ZH / … from keyword. Entire pipeline adapts: prompts, voice, subtitle font, filename slug.
- **Realtime feedback** — every pipeline step emits a WebSocket event.

**Non-goals:** timeline editor, CapCut clone, cloud sync, multi-user, project manager, asset library UI, custom motion editor, scene-level editing.

---

## 3. System Architecture

```
┌─────────────────────────────────────────────────────────────┐
│                    ELECTRON DESKTOP SHELL                    │
│                                                              │
│  ┌─────────────────────┐         ┌────────────────────────┐ │
│  │   React + Vite UI    │ ◄─────► │  FastAPI Python Sidecar│ │
│  │   (renderer process) │  HTTP   │   (spawned subprocess) │ │
│  │                      │   WS    │                        │ │
│  └─────────────────────┘         └────────────────────────┘ │
│           ▲                                  │              │
│           │ IPC                              │              │
│           ▼                                  ▼              │
│  ┌─────────────────────┐         ┌────────────────────────┐ │
│  │  Electron Main       │         │ LangGraph Agents       │ │
│  │  (folder picker,     │         │ Playwright + Chromium  │ │
│  │   file reveal,       │         │ FFmpeg subprocess      │ │
│  │   <video> player)    │         │ TTS / LLM clients      │ │
│  └─────────────────────┘         └────────────────────────┘ │
└─────────────────────────────────────────────────────────────┘
                       │
                       ▼
              ┌──────────────────────┐
              │ User Output          │
              │ D:\Videos\Karen\     │
              │   karen_viral_01.mp4 │
              │   karen_story_02.mp4 │
              └──────────────────────┘
```

**Process model:**
- **Electron main** — OS-level concerns: native folder dialog, shell.openPath / showItemInFolder, sidecar lifecycle.
- **Electron renderer (React UI)** — talks to FastAPI over `http://127.0.0.1:<port>`. Port allocated by main, passed via preload.
- **FastAPI sidecar** — `child_process.spawn` from main. Binds 127.0.0.1 only. Owns AI + render work. Killed on quit.
- **Playwright Chromium** — sidecar lazy-installs on first run, caches in app data dir.
- **FFmpeg** — invoked as subprocess. Bundled via `extraResources`.

Sidecar pattern: AI stack is more mature in Python and spec mandates FastAPI. Standard for production Electron+Python apps.

---

## 4. Tech Stack

**Frontend** — React 18 + Vite + TypeScript, Tailwind CSS, Framer Motion, Radix UI, Lucide Icons, Zustand (3 small stores: setup / job / preview).

**Desktop Shell** — Electron + `electron-vite`, `electron-builder` for installers (NSIS / dmg / AppImage). Preload with `contextIsolation: true`, narrow `window.api`.

**Backend** — FastAPI + Uvicorn (single worker, local). WebSocket built-in. Pydantic v2 (schemas → TS types). `httpx` async clients. `pydantic-settings` for env.

**Agent Layer** — LangGraph. Provider adapter pattern. **Default LLM: Gemini** (cheapest, matches reference tool). OpenAI + Claude adapters swappable via `LLM_PROVIDER` env.

**Rendering (HTML Scene + Playwright — confirmed via demo video reference)**
- **Playwright (Python) + bundled Chromium** — each scene is a self-contained HTML page with CSS/JS animations. Playwright launches headless Chromium, navigates, captures frames at target fps.
- **FFmpeg** — encodes frame sequence + voice + music + subtitles into MP4. Encoder/muxer, not compositor.
- **HTML templates per style** — Viral / Story / Explainer / Documentary / News / Cinematic. Scene Agent fills props per scene.
- Beats FFmpeg-only filters: motion graphics, animated text, neon, animated maps (reference output style) are impossible with FFmpeg alone.
- Beats Remotion: no Node runtime in Python sidecar, no React build per render.

**Voice (multi-lang)** — `edge-tts` default. Voice map by detected language: `vi-VN-HoaiMyNeural`, `en-US-AriaNeural`, `ja-JP-NanamiNeural`, `ko-KR-SunHiNeural`, `zh-CN-XiaoxiaoNeural`, etc. Each style picks a tone variant within the language's voice list.

**Subtitles & Fonts** — Generated from script + edge-tts word timestamps. ASS format (libass in FFmpeg). Templates ship **Noto Sans + Noto Sans CJK** via `@font-face` — covers Latin + VN + CJK without per-language template forks.

**Asset Sourcing** — Pexels / Pixabay / Unsplash adapters for scene **background images** (not video clips — Phase 1 renders motion graphics, not stock-footage composites). AI image gen adapter (Flux / DALL·E) stub for Phase 2+.

---

## 5. Repo Structure

```
ai-keyword-video-factory/
├── apps/desktop/                       # Electron shell
│   ├── electron/
│   │   ├── main.ts                     # spawn sidecar, dialogs, lifecycle
│   │   ├── preload.ts                  # window.api bridge
│   │   └── sidecar.ts                  # Python process manager
│   ├── src/
│   │   ├── App.tsx                     # single-screen root
│   │   ├── components/
│   │   │   ├── setup/                  # KeywordInput, IdeaCards, FormatPicker,
│   │   │   │                           # DurationSlider, CountStepper, StyleChips,
│   │   │   │                           # OutputFolderPicker, GenerateButton
│   │   │   ├── pipeline/               # PipelineGraph, PipelineNode
│   │   │   ├── status/                 # LiveStatus, CompactLog
│   │   │   ├── storyboard/             # StoryboardRail, SceneCard, VideoPreview
│   │   │   └── ui/                     # Radix-wrapped primitives
│   │   ├── store/                      # setupStore, jobStore, previewStore
│   │   ├── lib/                        # api.ts, ws.ts, types.ts
│   │   └── styles/globals.css
│   ├── electron.vite.config.ts
│   ├── tailwind.config.ts
│   └── package.json
│
├── backend/
│   ├── app/
│   │   ├── main.py                     # FastAPI entrypoint
│   │   ├── api/                        # ideas.py, render.py, ws.py
│   │   ├── agents/
│   │   │   ├── graph.py                # LangGraph state graph
│   │   │   ├── state.py                # JobState TypedDict
│   │   │   ├── language_detect.py      # first node
│   │   │   ├── research_agent.py
│   │   │   ├── idea_agent.py
│   │   │   ├── script_agent.py
│   │   │   ├── scene_agent.py          # picks template + props
│   │   │   └── asset_agent.py          # bg images only
│   │   ├── providers/
│   │   │   ├── llm/                    # base, gemini (default), openai, claude
│   │   │   ├── tts/                    # base, edge_tts, voice_map.py
│   │   │   └── assets/                 # base, pexels, pixabay, unsplash
│   │   ├── renderer/
│   │   │   ├── timeline.py             # Pydantic schema
│   │   │   ├── html_renderer.py        # Playwright frame capture
│   │   │   ├── ffmpeg_encoder.py       # frames + audio + subs → MP4
│   │   │   ├── subtitle.py             # ASS builder
│   │   │   └── job_queue.py            # bounded concurrent renderer
│   │   ├── templates/                  # HTML scene templates (per style)
│   │   │   ├── viral/                  # Phase 1: this only
│   │   │   │   ├── index.html
│   │   │   │   ├── style.css
│   │   │   │   └── scene.js
│   │   │   ├── story/                  # Phase 2: rest
│   │   │   ├── explainer/
│   │   │   ├── documentary/
│   │   │   ├── news/
│   │   │   └── cinematic/
│   │   ├── services/                   # job_manager, event_bus
│   │   ├── models/                     # Pydantic: job, idea, scene, render
│   │   ├── utils/                      # slug.py (multi-lang), lang.py
│   │   ├── config.py
│   │   └── logging_setup.py
│   ├── tests/
│   ├── pyproject.toml
│   └── README.md
│
├── assets/                             # bundled at install
│   ├── fonts/
│   │   ├── NotoSans-*.ttf              # Latin + Vietnamese
│   │   └── NotoSansCJK-*.otf           # CJK glyphs
│   └── music/                          # one royalty-free track per style
│       ├── viral_pulse.mp3
│       ├── story_ambient.mp3
│       ├── explainer_calm.mp3
│       ├── documentary_dramatic.mp3
│       ├── news_urgent.mp3
│       └── cinematic_orchestral.mp3
│
├── logs/                               # app.log, errors.log, jobs.jsonl
├── temp/                               # job_xxx/ scratch (cleaned post-render)
├── docs/                               # ARCHITECTURE.md, PLAN.md, UI_SPEC.md, API.md
├── reference-frames/                   # demo video frames (design reference)
└── README.md
```

---

## 6. AI Agent Pipeline (LangGraph)

```
        ┌──────────────┐
        │ Lang Detect  │   keyword → BCP-47 (vi / en / ja / ko / zh / …)
        └──────┬───────┘
        ┌──────▼───────┐
        │  Research    │   topic context, trends, angles (in detected lang)
        └──────┬───────┘
        ┌──────▼───────┐
        │  Idea Gen    │   N idea cards
        └──────┬───────┘
               │  (user picks idea, hits Generate)
        ┌──────▼───────┐
        │  Plan N      │   distribute styles across output_count
        │  Variants    │
        └──────┬───────┘
       ┌───────┴───────┐
       │  fan-out per  │   parallel branches
       │   video       │
       └───────┬───────┘
   ┌───────────┴───────────┐
   │  Script Agent (i)     │
   │  Scene Agent (i)      │   → picks template + scene props
   │  ┌─────────┬────────┐ │
   │  │ Voice   │ Asset  │ │   per-scene parallel
   │  │ Gen     │ Fetch  │ │   (bg-images only, not clips)
   │  └─────────┴────────┘ │
   │  Subtitle Build (i)   │
   │  Timeline Build (i)   │
   │  HTML Scene Render(i) │   ← Playwright frame capture
   │  FFmpeg Encode (i)    │   ← frames + audio + subs → MP4
   └───────────┬───────────┘
        ┌──────▼───────┐
        │  video.ready │
        └──────────────┘
```

**State shape:**
```python
class JobState(TypedDict):
    job_id: str
    keyword: str
    language: str                       # BCP-47, set by Lang Detect
    chosen_idea: Idea | None
    format: Literal["1:1","3:4","9:16","16:9"]
    duration_seconds: int
    output_count: int
    styles: list[str]
    output_folder: str
    research: ResearchOutput | None
    ideas: list[Idea]
    variants: list[VideoVariantState]   # one per output video
    errors: list[JobError]
```

**Language detection** — first node, before Research. Drives prompt language, TTS voice, subtitle encoding, filename slug.

**LLM adapter contract:**
```python
class LLMAdapter(Protocol):
    async def generate(
        self, *, system: str, prompt: str, json_schema: dict | None = None
    ) -> LLMResponse: ...
```
Switch provider via `LLM_PROVIDER=gemini|openai|claude` env. Default: `gemini`.

---

## 7. Render Pipeline

**Timeline JSON — contract between agents and renderer.** Pydantic both sides.

```json
{
  "version": 1,
  "job_id": "job_a1b2",
  "variant_id": "v01",
  "language": "vi",
  "style": "viral",
  "format": "9:16",
  "resolution": [1080, 1920],
  "fps": 30,
  "duration_seconds": 70,
  "audio": {
    "voice_track": "temp/job_a1b2/v01/voice.wav",
    "music_bed": "assets/music/viral_pulse.mp3",
    "music_gain_db": -22
  },
  "subtitles": { "path": "temp/job_a1b2/v01/subs.ass", "style": "viral_bold" },
  "scenes": [
    {
      "index": 0,
      "start": 0.0,
      "end": 5.2,
      "template": "viral",
      "props": {
        "headline": "KAREN UNLEASHED",
        "subhead": "What happened next will shock you",
        "background_image": "temp/job_a1b2/v01/scene_00_bg.jpg",
        "highlight_word_indices": [0, 1],
        "animation_seed": 4821
      }
    }
  ],
  "output_path": "D:\\Videos\\Karen\\karen_viral_01.mp4"
}
```

### Stage 1 — Per-scene HTML render
1. Pick template folder (`backend/app/templates/<style>/`).
2. Spawn Playwright Chromium page at target resolution.
3. Inject scene props via `await page.add_init_script("window.__SCENE__ = {...}")`.
4. Navigate to local `index.html` (served from in-process aiohttp on random port — avoids `file://` CORS).
5. Wait for `window.__SCENE_READY__ === true` (template sets after fonts + images loaded).
6. **Deterministic frame step-through:** each capture call advances CSS animations by `1/fps` via `document.getAnimations().forEach(a => a.currentTime = t * 1000)`. Frames as PNG in `temp/<job>/<variant>/scene_<i>/frames/`.
7. Emit `html.capture.progress` WS event per N frames.

Deterministic stepping (vs. real-time screenshot) makes render reproducible and immune to system jitter.

### Stage 2 — Per-scene encode to clip
```
ffmpeg -framerate 30 -i frames/%04d.png -c:v libx264 -pix_fmt yuv420p \
       -preset fast -crf 18 scene_<i>.mp4
```
HW accel preferred (NVENC / QSV / VideoToolbox).

### Stage 3 — Concat + audio + subtitles
```
ffmpeg -f concat -i clips.txt -i voice.wav -i music.mp3 \
       -filter_complex "[1:a]volume=1[v];[2:a]volume=0.12[m];[v][m]amix=2[a]" \
       -vf "subtitles=subs.ass" \
       -map 0:v -map "[a]" -c:v libx264 -c:a aac <output_path>
```

### Stage 4 — Atomic move to user folder
Move temp → user folder. Emit `video.ready`.

**Concurrency:** one HTML render per variant; `MAX_CONCURRENT_VARIANTS` (default 2) in parallel.

**Frame capture perf:**
- 1080×1920 PNG ~1.5MB → 70s × 30fps × 1.5MB ≈ 6.3GB temp / video.
- Mitigation: encode each scene immediately, delete frame folder.
- Target: under 1.5× realtime per variant on modern laptop.

**HTML template contract:**
- `index.html` reads `window.__SCENE__` for props.
- Sets `window.__SCENE_READY__ = true` after `document.fonts.ready` and bg image decoded.
- Only CSS Web Animations / `@keyframes` — NOT `setTimeout` / `setInterval`. Enables deterministic step-through.
- Ships `@font-face` (Noto Sans / Noto Sans CJK) — never system fonts.

**Output naming:** `<keyword_slug>_<style>_<NN>.mp4`

| Input | Output |
|---|---|
| `karen / viral / 1` | `karen_viral_01.mp4` |
| `tổng thống biden / story / 2` | `tong_thong_biden_story_02.mp4` |
| `韓国大統領 / explainer / 1` | `hangug-daetonglyeong_explainer_01.mp4` |

**Slug rules (`utils/slug.py`):**
1. Unicode NFKD → strip combining marks (Vietnamese diacritics gone).
2. CJK / non-Latin: try `unidecode` for romanization; if empty, fall back to `lang-<sha1[:8]>` keyed off original.
3. Lowercase, replace whitespace with `_`, strip outside `[a-z0-9_-]`, collapse `_`, max 40 chars.
4. If file exists → suffix with timestamp. Never overwrite.

Filesystem-safe on Windows / macOS / Linux regardless of input language.

---

## 8. API Contract

### REST

```
POST   /api/ideas/generate      { keyword } → { ideas, language }
POST   /api/render/start        RenderRequest → { job_id }
GET    /api/render/jobs/{id}    → JobSnapshot
POST   /api/render/jobs/{id}/cancel → { cancelled: true }
GET    /api/health              → { ok, version, ffmpeg, chromium, providers }
```

### WebSocket `/ws/render/{job_id}`

One channel per job. Server pushes. Client may send `ping` only.

**Envelope:** `{ "type": "...", "job_id": "...", "ts": 1747393200, "data": { ... } }`

| Event | Payload |
|---|---|
| `job.started` | `{ output_count, styles, language }` |
| `language.detected` | `{ language, confidence }` |
| `research.completed` | `{ summary, angles[] }` |
| `scripts.generated` | `{ variant_id, word_count, hook }` |
| `scenes.generated` | `{ variant_id, scene_count }` |
| `voice.generated` | `{ variant_id, duration_seconds }` |
| `html.capture.progress` | `{ variant_id, scene_index, frames_done, frames_total }` |
| `render.progress` | `{ variant_id, percent, fps, eta_seconds }` |
| `video.ready` | `{ variant_id, output_path }` |
| `job.completed` | `{ outputs: string[] }` |
| `job.error` | `{ stage, message, variant_id? }` |

**Reconnect:** UI keeps last seen `ts`; server replays buffered events since (in-memory per job, capped 500).

---

## 9. UI Layout

Single screen, desktop-first, min window 1280×800.

```
App.tsx
└── SingleScreenShell                     [grid: 360px | 1fr ; rows: 1fr]
    ├── LeftSetupPanel                    [overflow-y:auto, sticky generate]
    │   ├── KeywordInput
    │   ├── IdeaCards                     (collapsible after pick)
    │   ├── FormatPicker / DurationSlider / CountStepper / StyleChips
    │   ├── OutputFolderPicker
    │   └── GenerateButton                (sticky bottom)
    │
    └── CenterColumn                      [grid rows: auto | auto | 1fr]
        ├── PipelineGraph                 (LangDetect → Research → Idea → Script → Scene → Voice → HTML Render → Encode)
        ├── LiveStatusBar + CompactLog    (collapsible drawer up to 240px)
        └── StoryboardArea                [grid cols: 1fr 1.4fr]
            ├── StoryboardRail            (per-variant scene cards, horizontal scroll-snap)
            └── VideoPreview              (HTML5 <video> + fullscreen / speed / reveal)
```

**Layout rules:**
- Left panel: `min-height: 0; overflow-y: auto` — prevents flex blow-up.
- Center: CSS Grid with explicit row sizes; storyboard `1fr` scales.
- Compact log: `position: relative` collapsible — NEVER `position: fixed` (clips storyboard).
- Video preview: `aspect-ratio: var(--video-ar)` from selected format.
- Scene rail: `overflow-x:auto; scroll-snap-type:x mandatory`.
- Z-index scale: base 0, sticky 10, dropdowns 20, modals 50, tooltips 60. No `9999`.

**Design tokens (Tailwind):**

```
bg-app           #0A0A0B
bg-panel         #111114
bg-elevated      #17171B
border-subtle    #1F1F25
border-strong    #2A2A33
text-primary     #F5F5F7
text-secondary   #9B9BA8
text-muted       #5E5E6E
accent           #7C5CFF
accent-glow      rgba(124,92,255,0.35)
success          #34D399
warn             #F59E0B
error            #F87171
```

**Type:** Inter (Latin) + Noto Sans CJK (CJK), scale 12/13/14/16/20/28, tabular-nums for counters.

**Motion:** all 180–280ms, cubic-bezier(0.22, 1, 0.36, 1). Pipeline nodes pulse while active. Scene cards stagger-in on `scenes.generated`. Cross-fade preview on swap.

---

## 10. State Management

Three Zustand stores. No router. No Redux.

- **`setupStore`** — form state, persisted to `localStorage` (UI prefs only, not project state — allowed exception to "stateless").
- **`jobStore`** — current job snapshot, variants, per-variant progress, scenes, output paths. Wiped on new Generate.
- **`previewStore`** — selected variant, playback position, fullscreen.

WebSocket events dispatch via a single `applyEvent(event)` function — easy to test, easy to replay.

---

**See [PLAN.md](./PLAN.md) for phases, risks, verification, locked decisions, and next steps.**
