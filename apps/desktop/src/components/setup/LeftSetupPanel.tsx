import { useSetupStore } from '../../store/setupStore'
import { KeywordInput } from './KeywordInput'
import { IdeaCards } from './IdeaCards'
import { StyleChips } from './StyleChips'
import { OutputFolderPicker } from './OutputFolderPicker'
import { GenerateButton } from './GenerateButton'
import type { QualityMode } from '../../store/setupStore'

// Format options
const FORMATS = [
  { id: '9:16', label: '9:16', desc: 'Short / Reel' },
  { id: '16:9', label: '16:9', desc: 'YouTube' },
  { id: '1:1',  label: '1:1',  desc: 'Square' },
] as const

// Duration presets in seconds
const DURATIONS = [15, 30, 60, 90] as const

// Quality mode options
const QUALITY_OPTS: { id: QualityMode; label: string; desc: string }[] = [
  { id: 'preview', label: 'Preview', desc: '480p · fast' },
  { id: 'final',   label: 'Final',   desc: '1080p · HQ'  },
]

export function LeftSetupPanel() {
  const format = useSetupStore((s) => s.format)
  const setFormat = useSetupStore((s) => s.setFormat)
  const durationSeconds = useSetupStore((s) => s.durationSeconds)
  const setDuration = useSetupStore((s) => s.setDuration)
  const outputCount = useSetupStore((s) => s.outputCount)
  const setOutputCount = useSetupStore((s) => s.setOutputCount)
  const qualityMode = useSetupStore((s) => s.qualityMode)
  const setQualityMode = useSetupStore((s) => s.setQualityMode)

  return (
    <div className="flex flex-col h-full">
      {/* Scrollable form area */}
      <div className="flex-1 overflow-y-auto px-4 py-4 flex flex-col gap-5">
        {/* Header */}
        <div>
          <h2 className="text-base font-semibold text-primary">New Generation</h2>
          <p className="text-xs text-muted mt-0.5">Keyword → Multiple finished MP4s</p>
        </div>

        <div className="h-px bg-subtle" />

        {/* Keyword */}
        <KeywordInput />

        {/* Idea cards — auto-generate after keyword is entered */}
        <IdeaCards />

        {/* Format picker */}
        <div className="flex flex-col gap-2">
          <label className="text-xs font-semibold text-muted uppercase tracking-wider">
            Format
          </label>
          <div className="flex gap-1.5">
            {FORMATS.map(({ id, label, desc }) => (
              <button
                key={id}
                onClick={() => setFormat(id as typeof format)}
                className={[
                  'flex-1 flex flex-col items-center py-2 rounded-lg border text-xs font-medium transition-all',
                  format === id
                    ? 'bg-accent/10 border-accent text-accent'
                    : 'bg-elevated border-subtle text-muted hover:border-accent/40 hover:text-secondary',
                ].join(' ')}
              >
                <span className="font-bold">{label}</span>
                <span className="text-2xs opacity-70 mt-0.5">{desc}</span>
              </button>
            ))}
          </div>
        </div>

        {/* Duration presets */}
        <div className="flex flex-col gap-2">
          <div className="flex items-center justify-between">
            <label className="text-xs font-semibold text-muted uppercase tracking-wider">
              Duration
            </label>
            <span className="text-xs text-secondary tabular">{durationSeconds}s</span>
          </div>
          <div className="flex gap-1.5">
            {DURATIONS.map((d) => (
              <button
                key={d}
                onClick={() => setDuration(d)}
                className={[
                  'flex-1 py-1.5 rounded-md border text-xs font-medium transition-all',
                  durationSeconds === d
                    ? 'bg-accent/10 border-accent text-accent'
                    : 'bg-elevated border-subtle text-muted hover:border-accent/40',
                ].join(' ')}
              >
                {d}s
              </button>
            ))}
          </div>
        </div>

        {/* Output count stepper */}
        <div className="flex flex-col gap-2">
          <label className="text-xs font-semibold text-muted uppercase tracking-wider">
            Output Count
          </label>
          <div className="flex items-center gap-3">
            <button
              onClick={() => setOutputCount(outputCount - 1)}
              disabled={outputCount <= 1}
              className="w-8 h-8 flex items-center justify-center rounded-md bg-elevated border border-subtle text-secondary hover:text-primary hover:border-accent/50 disabled:opacity-30 disabled:cursor-not-allowed transition-all"
            >
              −
            </button>
            <span className="flex-1 text-center text-base font-semibold tabular text-primary">
              {outputCount}
            </span>
            <button
              onClick={() => setOutputCount(outputCount + 1)}
              disabled={outputCount >= 10}
              className="w-8 h-8 flex items-center justify-center rounded-md bg-elevated border border-subtle text-secondary hover:text-primary hover:border-accent/50 disabled:opacity-30 disabled:cursor-not-allowed transition-all"
            >
              +
            </button>
          </div>
          <p className="text-2xs text-muted">
            {outputCount === 1 ? '1 video' : `${outputCount} distinct videos`} per run
          </p>
        </div>

        {/* Style chips */}
        <StyleChips />

        {/* Quality mode */}
        <div className="flex flex-col gap-2">
          <label className="text-xs font-semibold text-muted uppercase tracking-wider">
            Quality
          </label>
          <div className="flex gap-1.5">
            {QUALITY_OPTS.map(({ id, label, desc }) => (
              <button
                key={id}
                onClick={() => setQualityMode(id)}
                className={[
                  'flex-1 flex flex-col items-center py-2 rounded-lg border text-xs font-medium transition-all',
                  qualityMode === id
                    ? 'bg-accent/10 border-accent text-accent'
                    : 'bg-elevated border-subtle text-muted hover:border-accent/40 hover:text-secondary',
                ].join(' ')}
              >
                <span className="font-bold">{label}</span>
                <span className="text-2xs opacity-70 mt-0.5">{desc}</span>
              </button>
            ))}
          </div>
        </div>

        {/* Output folder */}
        <OutputFolderPicker />
      </div>

      {/* Sticky Generate button */}
      <div className="px-4 pb-4 pt-3 border-t border-subtle flex-shrink-0">
        <GenerateButton />
      </div>
    </div>
  )
}
