import { useEffect, useRef } from 'react'
import { motion, AnimatePresence } from 'framer-motion'
import { Sparkles, Loader2, TrendingUp, CheckCircle2 } from 'lucide-react'
import { useSetupStore } from '../../store/setupStore'
import { generateIdeas } from '../../lib/api'
import type { Idea } from '../../lib/types'

// Locally-generated fallback ideas (no API call needed)
function buildFallbackIdeas(keyword: string): Idea[] {
  const kw = keyword.trim()
  return [
    {
      id: 'local-0',
      title: `${kw} — The Untold Story`,
      angle: 'controversy',
      hook: `What nobody tells you about ${kw}`,
      estimated_views: '500K–2M',
    },
    {
      id: 'local-1',
      title: `The Rise of ${kw}`,
      angle: 'timeline',
      hook: `How ${kw} changed everything in 60 seconds`,
      estimated_views: '200K–800K',
    },
    {
      id: 'local-2',
      title: `${kw} Exposed`,
      angle: 'viral_hook',
      hook: `You won't believe what ${kw} did next`,
      estimated_views: '1M–5M',
    },
  ]
}

export function IdeaCards() {
  const keyword = useSetupStore((s) => s.keyword)
  const ideas = useSetupStore((s) => s.ideas)
  const selectedIdeaId = useSetupStore((s) => s.selectedIdeaId)
  const isLoadingIdeas = useSetupStore((s) => s.isLoadingIdeas)
  const setIdeas = useSetupStore((s) => s.setIdeas)
  const setSelectedIdeaId = useSetupStore((s) => s.setSelectedIdeaId)
  const setIsLoadingIdeas = useSetupStore((s) => s.setIsLoadingIdeas)
  const clearIdeas = useSetupStore((s) => s.clearIdeas)

  // Debounce: auto-fetch ideas 800ms after keyword settles
  const timerRef = useRef<ReturnType<typeof setTimeout> | null>(null)

  useEffect(() => {
    if (timerRef.current) clearTimeout(timerRef.current)

    const trimmed = keyword.trim()
    if (trimmed.length < 2) {
      clearIdeas()
      return
    }

    // Reset selection immediately when keyword changes
    setSelectedIdeaId(null)

    timerRef.current = setTimeout(async () => {
      setIsLoadingIdeas(true)
      try {
        const result = await generateIdeas(trimmed)
        const list = result.ideas.length > 0 ? result.ideas : buildFallbackIdeas(trimmed)
        setIdeas(list)
        // Auto-select first idea for this new keyword
        if (list.length > 0) setSelectedIdeaId(list[0].id)
      } catch {
        // Backend not ready or failed — use local fallback, silently
        const fallback = buildFallbackIdeas(trimmed)
        setIdeas(fallback)
        if (fallback.length > 0) setSelectedIdeaId(fallback[0].id)
      } finally {
        setIsLoadingIdeas(false)
      }
    }, 800)

    return () => {
      if (timerRef.current) clearTimeout(timerRef.current)
    }
  }, [keyword]) // eslint-disable-line react-hooks/exhaustive-deps

  const trimmedKeyword = keyword.trim()
  if (trimmedKeyword.length < 2) return null

  return (
    <div className="flex flex-col gap-2">
      {/* Section header */}
      <div className="flex items-center justify-between">
        <label className="text-xs font-semibold text-muted uppercase tracking-wider">
          Video Idea
        </label>
        {isLoadingIdeas && (
          <div className="flex items-center gap-1 text-2xs text-accent">
            <Loader2 size={10} className="animate-spin" />
            <span>Generating…</span>
          </div>
        )}
        {!isLoadingIdeas && ideas.length > 0 && (
          <div className="flex items-center gap-1 text-2xs text-muted">
            <Sparkles size={10} />
            <span>AI ideas</span>
          </div>
        )}
      </div>

      {/* Skeleton while loading */}
      {isLoadingIdeas && ideas.length === 0 && (
        <div className="flex flex-col gap-1.5">
          {[0, 1, 2].map((i) => (
            <div
              key={i}
              className="h-14 rounded-lg bg-elevated border border-subtle animate-pulse"
              style={{ animationDelay: `${i * 80}ms` }}
            />
          ))}
        </div>
      )}

      {/* Idea cards */}
      <AnimatePresence>
        {!isLoadingIdeas && ideas.length > 0 && (
          <div className="flex flex-col gap-1.5">
            {ideas.map((idea, i) => (
              <IdeaCard
                key={idea.id}
                idea={idea}
                index={i}
                isSelected={selectedIdeaId === idea.id}
                onSelect={() => setSelectedIdeaId(idea.id)}
              />
            ))}
          </div>
        )}
      </AnimatePresence>
    </div>
  )
}

function IdeaCard({
  idea,
  index,
  isSelected,
  onSelect,
}: {
  idea: Idea
  index: number
  isSelected: boolean
  onSelect: () => void
}) {
  return (
    <motion.button
      initial={{ opacity: 0, y: 8 }}
      animate={{ opacity: 1, y: 0 }}
      transition={{ duration: 0.22, delay: index * 0.05, ease: [0.22, 1, 0.36, 1] }}
      onClick={onSelect}
      className={[
        'w-full flex items-start gap-2.5 px-3 py-2.5 rounded-lg border text-left transition-all duration-200',
        isSelected
          ? 'bg-accent/10 border-accent ring-1 ring-accent/20'
          : 'bg-elevated border-subtle hover:border-accent/40 hover:bg-elevated/80',
      ].join(' ')}
    >
      {/* Selection indicator */}
      <div className="flex-shrink-0 mt-0.5">
        {isSelected ? (
          <CheckCircle2 size={13} className="text-accent" />
        ) : (
          <div className="w-3.5 h-3.5 rounded-full border border-muted/50 bg-elevated" />
        )}
      </div>

      {/* Content */}
      <div className="flex-1 min-w-0">
        <p className={`text-xs font-semibold leading-tight truncate ${isSelected ? 'text-accent' : 'text-primary'}`}>
          {idea.title}
        </p>
        <p className="text-2xs text-muted mt-0.5 leading-relaxed line-clamp-1">
          {idea.hook}
        </p>
      </div>

      {/* Est views */}
      <div className="flex-shrink-0 flex items-center gap-0.5 text-2xs text-muted opacity-70">
        <TrendingUp size={9} />
        <span className="tabular">{idea.estimated_views}</span>
      </div>
    </motion.button>
  )
}
