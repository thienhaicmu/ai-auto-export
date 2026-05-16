import { motion } from 'framer-motion'
import { CheckCircle2, Loader2, AlertCircle, Film } from 'lucide-react'
import { useJobStore } from '../../store/jobStore'
import { usePreviewStore } from '../../store/previewStore'
import type { JobVariant } from '../../lib/types'

export function StoryboardRail() {
  const job = useJobStore((s) => s.job)
  const variants = job?.variants ?? []
  const selectedId = usePreviewStore((s) => s.selectedVariantId)
  const selectVariant = usePreviewStore((s) => s.selectVariant)

  if (!job) {
    return (
      <div className="flex flex-col items-center justify-center h-full gap-3 text-muted px-8">
        <Film size={32} className="opacity-20" />
        <p className="text-xs text-center">
          Enter a keyword and click Generate to create your videos
        </p>
      </div>
    )
  }

  if (variants.length === 0) {
    return (
      <div className="flex items-center justify-center h-full">
        <Loader2 size={20} className="text-accent animate-spin" />
      </div>
    )
  }

  return (
    <div className="flex flex-col h-full">
      <div className="px-4 py-2 border-b border-subtle flex-shrink-0">
        <span className="text-xs font-semibold text-muted uppercase tracking-wider">
          Variants ({variants.length})
        </span>
      </div>

      <div
        className="flex-1 overflow-x-auto overflow-y-hidden p-4"
        style={{
          scrollSnapType: 'x mandatory',
          display: 'grid',
          gridAutoFlow: 'column',
          gridAutoColumns: '160px',
          gap: '12px',
          alignContent: 'start',
        }}
      >
        {variants.map((variant, i) => (
          <VariantCard
            key={variant.variant_id}
            variant={variant}
            index={i}
            isSelected={selectedId === variant.variant_id}
            onSelect={() => selectVariant(variant.variant_id)}
          />
        ))}
      </div>
    </div>
  )
}

function VariantCard({
  variant,
  index,
  isSelected,
  onSelect,
}: {
  variant: JobVariant
  index: number
  isSelected: boolean
  onSelect: () => void
}) {
  const style = {
    scrollSnapAlign: 'start' as const,
    animationDelay: `${index * 60}ms`,
  }

  return (
    <motion.button
      initial={{ opacity: 0, y: 12 }}
      animate={{ opacity: 1, y: 0 }}
      transition={{ duration: 0.28, delay: index * 0.06, ease: [0.22, 1, 0.36, 1] }}
      onClick={onSelect}
      style={style}
      className={[
        'flex flex-col rounded-xl border overflow-hidden transition-all duration-200 text-left',
        isSelected
          ? 'border-accent ring-1 ring-accent/30 bg-elevated'
          : 'border-subtle bg-elevated hover:border-accent/40',
      ].join(' ')}
    >
      {/* Thumbnail area */}
      <div
        className="relative flex items-center justify-center bg-app"
        style={{ aspectRatio: '9/16', width: '100%' }}
      >
        {/* Placeholder thumbnail — real thumbnails from Phase 2 */}
        <div className="absolute inset-0 bg-gradient-to-b from-[#17171B] to-[#0A0A0B]" />
        <div className="relative z-10 flex flex-col items-center gap-2">
          <StatusIcon status={variant.status} />
          {variant.status === 'running' && variant.progress > 0 && (
            <span className="text-xs tabular text-accent font-semibold">
              {variant.progress}%
            </span>
          )}
        </div>

        {/* Progress bar overlay */}
        {variant.status === 'running' && (
          <div className="absolute bottom-0 left-0 right-0 h-0.5 bg-subtle">
            <motion.div
              className="h-full bg-accent"
              initial={{ width: 0 }}
              animate={{ width: `${variant.progress}%` }}
              transition={{ duration: 0.5 }}
            />
          </div>
        )}

        {/* Style badge */}
        <div className="absolute top-2 left-2 px-1.5 py-0.5 rounded bg-black/60 text-2xs text-secondary font-medium uppercase tracking-wide">
          {variant.style}
        </div>
      </div>

      {/* Info footer */}
      <div className="px-2.5 py-2 flex flex-col gap-0.5">
        <span className="text-xs font-semibold text-primary truncate">
          Variant {String(index + 1).padStart(2, '0')}
        </span>
        {variant.hook && (
          <span className="text-2xs text-muted line-clamp-2 leading-relaxed">
            {variant.hook}
          </span>
        )}
      </div>
    </motion.button>
  )
}

function StatusIcon({ status }: { status: JobVariant['status'] }) {
  switch (status) {
    case 'done':
      return <CheckCircle2 size={24} className="text-success" />
    case 'running':
      return <Loader2 size={20} className="text-accent animate-spin" />
    case 'error':
      return <AlertCircle size={24} className="text-error" />
    default:
      return <Film size={20} className="text-muted opacity-40" />
  }
}
