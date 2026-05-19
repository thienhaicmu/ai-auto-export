// WS event types — mirrors ARCHITECTURE.md §8 + Phase 4A audio events
export type WsEventType =
  | 'job.started'
  | 'language.detected'
  | 'research.completed'
  | 'scripts.generated'
  | 'scenes.generated'
  | 'assets.selected'
  | 'voice.generated'
  | 'audio.timeline.generated'
  | 'html.capture.progress'
  | 'render.progress'
  | 'audio.mixed'
  | 'video.ready'
  | 'job.completed'
  | 'job.error'
  | 'ping'

export interface WsEvent {
  type: WsEventType
  job_id: string
  ts: number
  data: Record<string, unknown>
}

export type VideoFormat = '1:1' | '3:4' | '9:16' | '16:9'
export type VideoStyle = 'viral' | 'story' | 'explainer' | 'documentary' | 'news' | 'cinematic'
export type JobStatus = 'idle' | 'running' | 'completed' | 'error'
export type VariantStatus = 'pending' | 'running' | 'done' | 'error'

export interface SceneSnapshot {
  index: number
  headline?: string
  thumbnailPath?: string
}

export interface JobVariant {
  variant_id: string
  style: VideoStyle
  progress: number
  status: VariantStatus
  outputPath: string | null
  scenes: SceneSnapshot[]
  hook: string | null
  wordCount: number | null
}

export interface JobSnapshot {
  job_id: string
  keyword: string
  status: JobStatus
  language: string | null
  variants: JobVariant[]
  events: WsEvent[]
}

export interface Idea {
  id: string
  title: string
  angle: string
  hook: string
  estimated_views: string
}

export interface HealthStatus {
  ok: boolean
  version: string
  ffmpeg: boolean
  chromium: boolean
  providers: { llm: string; tts: string }
}
