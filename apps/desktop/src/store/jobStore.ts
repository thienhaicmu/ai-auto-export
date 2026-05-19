import { create } from 'zustand'
import type { WsEvent, JobSnapshot, JobVariant, VariantStatus } from '../lib/types'

interface JobState {
  job: JobSnapshot | null
  isGenerating: boolean

  startJob: (jobId: string, keyword: string) => void
  applyEvent: (event: WsEvent) => void
  reset: () => void
}

// Pure reducer — easy to unit-test independently
export function applyEventToJob(job: JobSnapshot, event: WsEvent): JobSnapshot {
  const events = [...job.events, event]

  switch (event.type) {
    case 'job.started':
      return { ...job, status: 'running', events }

    case 'language.detected':
      return { ...job, language: event.data.language as string, events }

    case 'research.completed':
      return { ...job, events }

    case 'scripts.generated': {
      const vid = event.data.variant_id as string
      return {
        ...job,
        events,
        variants: upsertVariant(job.variants, vid, (v) => ({
          ...v,
          status: 'running' as VariantStatus,
          hook: event.data.hook as string,
          wordCount: event.data.word_count as number,
        })),
      }
    }

    case 'scenes.generated': {
      const vid = event.data.variant_id as string
      return {
        ...job,
        events,
        variants: upsertVariant(job.variants, vid, (v) => ({ ...v })),
      }
    }

    case 'assets.selected':
      return { ...job, events }

    case 'voice.generated':
      return { ...job, events }

    case 'audio.timeline.generated':
      return { ...job, events }

    case 'html.capture.progress': {
      const vid = event.data.variant_id as string
      const done = event.data.frames_done as number
      const total = event.data.frames_total as number
      const pct = total > 0 ? Math.round((done / total) * 100) : 0
      return {
        ...job,
        events,
        variants: upsertVariant(job.variants, vid, (v) => ({ ...v, progress: pct })),
      }
    }

    case 'render.progress': {
      const vid = event.data.variant_id as string
      const pct = event.data.percent as number
      return {
        ...job,
        events,
        variants: upsertVariant(job.variants, vid, (v) => ({ ...v, progress: pct })),
      }
    }

    case 'audio.mixed':
      return { ...job, events }

    case 'video.ready': {
      const vid = event.data.variant_id as string
      return {
        ...job,
        events,
        variants: upsertVariant(job.variants, vid, (v) => ({
          ...v,
          status: 'done' as VariantStatus,
          progress: 100,
          outputPath: event.data.output_path as string,
        })),
      }
    }

    case 'job.completed':
      return { ...job, status: 'completed', events }

    case 'job.error':
      return { ...job, status: 'error', events }

    default:
      return { ...job, events }
  }
}

function upsertVariant(
  variants: JobVariant[],
  variantId: string,
  update: (v: JobVariant) => JobVariant
): JobVariant[] {
  const existing = variants.find((v) => v.variant_id === variantId)
  if (existing) {
    return variants.map((v) => (v.variant_id === variantId ? update(v) : v))
  }
  const blank: JobVariant = {
    variant_id: variantId,
    style: 'viral',
    progress: 0,
    status: 'pending',
    outputPath: null,
    scenes: [],
    hook: null,
    wordCount: null,
  }
  return [...variants, update(blank)]
}

export const useJobStore = create<JobState>()((set) => ({
  job: null,
  isGenerating: false,

  startJob: (jobId, keyword) =>
    set({
      isGenerating: true,
      job: {
        job_id: jobId,
        keyword,
        status: 'idle',
        language: null,
        variants: [],
        events: [],
      },
    }),

  applyEvent: (event) =>
    set((state) => {
      if (!state.job) return state
      const job = applyEventToJob(state.job, event)
      return {
        job,
        isGenerating: job.status !== 'completed' && job.status !== 'error',
      }
    }),

  reset: () => set({ job: null, isGenerating: false }),
}))
