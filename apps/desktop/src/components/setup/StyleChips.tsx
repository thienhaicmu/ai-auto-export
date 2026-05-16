import { useSetupStore } from '../../store/setupStore'
import type { VideoStyle } from '../../lib/types'

const STYLES: { id: VideoStyle; label: string; emoji: string; phase: number }[] = [
  { id: 'viral',       label: 'Viral',       emoji: '⚡', phase: 1 },
  { id: 'story',       label: 'Story',       emoji: '📖', phase: 2 },
  { id: 'explainer',  label: 'Explainer',   emoji: '🎓', phase: 2 },
  { id: 'documentary',label: 'Documentary', emoji: '🎬', phase: 2 },
  { id: 'news',        label: 'News',        emoji: '📰', phase: 2 },
  { id: 'cinematic',   label: 'Cinematic',   emoji: '🎥', phase: 2 },
]

export function StyleChips() {
  const styles = useSetupStore((s) => s.styles)
  const toggleStyle = useSetupStore((s) => s.toggleStyle)

  return (
    <div className="flex flex-col gap-2">
      <label className="text-xs font-semibold text-muted uppercase tracking-wider">
        Style
      </label>
      <div className="flex flex-wrap gap-1.5">
        {STYLES.map(({ id, label, emoji, phase }) => {
          const active = styles.includes(id)
          const locked = phase > 1
          return (
            <button
              key={id}
              onClick={() => !locked && toggleStyle(id)}
              disabled={locked}
              title={locked ? 'Phase 2' : label}
              className={[
                'flex items-center gap-1 px-2.5 py-1 rounded-md text-xs font-medium transition-all',
                locked
                  ? 'opacity-30 cursor-not-allowed border border-subtle text-muted'
                  : active
                    ? 'bg-accent text-white border border-accent shadow-sm glow-accent'
                    : 'bg-elevated border border-subtle text-secondary hover:border-accent/50 hover:text-primary',
              ].join(' ')}
            >
              <span>{emoji}</span>
              <span>{label}</span>
            </button>
          )
        })}
      </div>
    </div>
  )
}
