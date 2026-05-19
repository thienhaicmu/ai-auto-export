import { useState, useRef, useEffect } from 'react'
import { ChevronDown, ChevronUp } from 'lucide-react'
import { useJobStore } from '../../store/jobStore'
import type { WsEvent } from '../../lib/types'

const EVENT_COLORS: Partial<Record<string, string>> = {
  'job.started':              'text-secondary',
  'language.detected':        'text-secondary',
  'research.completed':       'text-accent',
  'scripts.generated':        'text-accent',
  'scenes.generated':         'text-accent',
  'assets.selected':          'text-secondary',
  'voice.generated':          'text-accent',
  'audio.timeline.generated': 'text-accent',
  'html.capture.progress':    'text-warn',
  'render.progress':          'text-warn',
  'audio.mixed':              'text-accent',
  'video.ready':              'text-success',
  'job.completed':            'text-success',
  'job.error':                'text-error',
}

function formatEvent(e: WsEvent): string {
  switch (e.type) {
    case 'job.started':
      return `Job started — quality: ${e.data.quality_mode ?? 'final'}`
    case 'language.detected':
      return `Language detected: ${e.data.language} (${Math.round((e.data.confidence as number) * 100)}%)`
    case 'research.completed':
      return `Research: ${e.data.summary}`
    case 'scripts.generated':
      return `Script ready [${e.data.variant_id}] — ${e.data.word_count} words — "${e.data.hook}"`
    case 'scenes.generated':
      return `${e.data.scene_count} scenes generated [${e.data.variant_id}]`
    case 'assets.selected':
      return `Assets selected [${e.data.variant_id}] — ${e.data.assets_found}/${e.data.total_scenes} scenes`
    case 'voice.generated':
      return `Voice ready [${e.data.variant_id}] — ${e.data.duration_seconds}s`
    case 'audio.timeline.generated':
      return `Audio timeline — ${e.data.bpm} BPM, ${e.data.beat_count} beats`
    case 'html.capture.progress': {
      const pct = Math.round(((e.data.frames_done as number) / (e.data.frames_total as number)) * 100)
      return `Capturing [${e.data.variant_id}] scene ${e.data.scene_index} — ${pct}%`
    }
    case 'render.progress':
      return `Encoding [${e.data.variant_id}] — ${e.data.percent}%`
    case 'audio.mixed':
      return `Audio mixed [${e.data.variant_id}] — music: ${e.data.has_music ? 'yes' : 'no'}, ducking: ${e.data.duck_voice ? 'on' : 'off'}`
    case 'video.ready':
      return `Video ready [${e.data.variant_id}] → ${e.data.output_path}`
    case 'job.completed':
      return `Job complete — ${(e.data.outputs as string[]).length} video(s) exported`
    case 'job.error':
      return `Error at ${e.data.stage}: ${e.data.message}`
    default:
      return e.type.replace(/\./g, ' ')
  }
}

export function LiveStatus() {
  const [collapsed, setCollapsed] = useState(false)
  const events = useJobStore((s) => s.job?.events ?? [])
  const jobStatus = useJobStore((s) => s.job?.status ?? null)
  const logRef = useRef<HTMLDivElement>(null)

  // Auto-scroll to bottom on new events
  useEffect(() => {
    if (logRef.current && !collapsed) {
      logRef.current.scrollTop = logRef.current.scrollHeight
    }
  }, [events.length, collapsed])

  const visibleEvents = events.filter((e) => e.type !== 'ping')

  // Error from job.error event
  const errorEvent = visibleEvents.find((e) => e.type === 'job.error')

  return (
    <div className="flex flex-col">
      {/* Terminal error banner — shown when job fails */}
      {jobStatus === 'error' && errorEvent && (
        <div className="px-5 py-2 bg-error/10 border-b border-error/20 flex items-start gap-2">
          <span className="text-xs text-error flex-shrink-0 font-semibold mt-px">✕</span>
          <p className="text-xs text-error leading-relaxed">
            {`Error at ${errorEvent.data.stage}: ${errorEvent.data.message}`}
          </p>
        </div>
      )}

      {/* Success banner */}
      {jobStatus === 'completed' && (
        <div className="px-5 py-2 bg-success/10 border-b border-success/20">
          <p className="text-xs text-success font-medium">
            ✓ All videos exported successfully
          </p>
        </div>
      )}

      {/* Header / toggle */}
      <button
        onClick={() => setCollapsed((c) => !c)}
        className="flex items-center justify-between px-5 py-2 text-xs text-muted hover:text-secondary transition-colors no-select"
      >
        <span className="font-semibold uppercase tracking-wider">Live Log</span>
        <div className="flex items-center gap-2">
          {visibleEvents.length > 0 && (
            <span className="tabular text-muted">{visibleEvents.length} events</span>
          )}
          {collapsed ? <ChevronDown size={12} /> : <ChevronUp size={12} />}
        </div>
      </button>

      {!collapsed && (
        <div
          ref={logRef}
          className="overflow-y-auto px-5 pb-2"
          style={{ maxHeight: '180px' }}
        >
          {visibleEvents.length === 0 ? (
            <p className="text-xs text-muted py-2">
              Waiting for pipeline events…
            </p>
          ) : (
            <div className="flex flex-col gap-0.5 font-mono">
              {visibleEvents.map((e, i) => (
                <div key={i} className="flex items-start gap-2 text-xs">
                  <span className="text-muted flex-shrink-0 tabular" style={{ minWidth: 60 }}>
                    {new Date(e.ts * 1000).toLocaleTimeString([], {
                      hour: '2-digit',
                      minute: '2-digit',
                      second: '2-digit',
                    })}
                  </span>
                  <span className={`flex-1 ${EVENT_COLORS[e.type] ?? 'text-secondary'}`}>
                    {formatEvent(e)}
                  </span>
                </div>
              ))}
            </div>
          )}
        </div>
      )}
    </div>
  )
}
