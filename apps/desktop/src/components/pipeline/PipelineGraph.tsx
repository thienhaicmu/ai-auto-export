import { useJobStore } from '../../store/jobStore'
import type { WsEventType } from '../../lib/types'

// Pipeline stages: maps to WS event types that "complete" each node
const STAGES: { id: string; label: string; completedBy: WsEventType[] }[] = [
  { id: 'lang',    label: 'Lang Detect',  completedBy: ['language.detected'] },
  { id: 'research',label: 'Research',     completedBy: ['research.completed'] },
  { id: 'ideas',   label: 'Ideas',        completedBy: ['scripts.generated'] },
  { id: 'script',  label: 'Script',       completedBy: ['scripts.generated'] },
  { id: 'scene',   label: 'Scene',        completedBy: ['scenes.generated'] },
  { id: 'voice',   label: 'Voice',        completedBy: ['voice.generated'] },
  { id: 'render',  label: 'HTML Render',  completedBy: ['html.capture.progress', 'render.progress'] },
  { id: 'encode',  label: 'Encode',       completedBy: ['video.ready'] },
]

type NodeState = 'idle' | 'active' | 'done' | 'error'

function getNodeState(
  stageIdx: number,
  completedStages: Set<number>,
  activeStage: number | null,
  hasError: boolean
): NodeState {
  if (completedStages.has(stageIdx)) return 'done'
  if (activeStage === stageIdx) return hasError ? 'error' : 'active'
  return 'idle'
}

export function PipelineGraph() {
  const job = useJobStore((s) => s.job)
  const events = job?.events ?? []

  // Derive which stages are done from emitted events
  const completedStages = new Set<number>()
  let activeStage: number | null = null

  if (job?.status === 'running' || job?.status === 'completed') {
    const seenTypes = new Set(events.map((e) => e.type))
    STAGES.forEach((stage, idx) => {
      if (stage.completedBy.some((t) => seenTypes.has(t))) {
        completedStages.add(idx)
      }
    })

    // Active = first stage whose completion event hasn't arrived yet
    if (job.status === 'running') {
      for (let i = 0; i < STAGES.length; i++) {
        if (!completedStages.has(i)) { activeStage = i; break }
      }
    }
  }

  const hasError = job?.status === 'error'

  return (
    <div className="flex items-center gap-0 overflow-x-auto no-select" style={{ scrollbarWidth: 'none' }}>
      {STAGES.map((stage, idx) => {
        const state = getNodeState(idx, completedStages, activeStage, hasError)
        return (
          <div key={stage.id} className="flex items-center">
            <StageNode label={stage.label} state={state} />
            {idx < STAGES.length - 1 && (
              <div
                className={`w-6 h-px transition-colors ${
                  completedStages.has(idx) ? 'bg-accent/60' : 'bg-subtle'
                }`}
              />
            )}
          </div>
        )
      })}
    </div>
  )
}

function StageNode({ label, state }: { label: string; state: NodeState }) {
  const base = 'flex items-center gap-1.5 px-2.5 py-1 rounded-md border text-xs font-medium transition-all duration-200'
  const styles: Record<NodeState, string> = {
    idle:   'bg-elevated border-subtle text-muted',
    active: 'bg-accent/10 border-accent text-accent node-active',
    done:   'bg-success/10 border-success/30 text-success',
    error:  'bg-error/10 border-error/30 text-error',
  }
  const dots: Record<NodeState, string> = {
    idle:   'bg-muted/40',
    active: 'bg-accent animate-pulse',
    done:   'bg-success',
    error:  'bg-error',
  }

  return (
    <div className={`${base} ${styles[state]}`}>
      <div className={`w-1.5 h-1.5 rounded-full flex-shrink-0 ${dots[state]}`} />
      <span className="whitespace-nowrap">{label}</span>
    </div>
  )
}
