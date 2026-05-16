import { motion, AnimatePresence } from 'framer-motion'
import { Zap, Loader2 } from 'lucide-react'
import { useSetupStore } from '../../store/setupStore'
import { useJobStore } from '../../store/jobStore'
import { usePreviewStore } from '../../store/previewStore'
import { startRender } from '../../lib/api'
import { connectJobWs, disconnectJobWs } from '../../lib/ws'

export function GenerateButton() {
  const keyword = useSetupStore((s) => s.keyword)
  const format = useSetupStore((s) => s.format)
  const durationSeconds = useSetupStore((s) => s.durationSeconds)
  const outputCount = useSetupStore((s) => s.outputCount)
  const styles = useSetupStore((s) => s.styles)
  const outputFolder = useSetupStore((s) => s.outputFolder)

  const isGenerating = useJobStore((s) => s.isGenerating)
  const startJob = useJobStore((s) => s.startJob)
  const reset = useJobStore((s) => s.reset)
  const clearPreview = usePreviewStore((s) => s.clear)

  const canGenerate = keyword.trim().length > 0 && !isGenerating

  async function handleGenerate() {
    if (!canGenerate) return
    disconnectJobWs()
    reset()
    clearPreview()

    try {
      const { job_id } = await startRender({
        keyword: keyword.trim(),
        format,
        duration_seconds: durationSeconds,
        output_count: outputCount,
        styles,
        output_folder: outputFolder,
      })
      startJob(job_id, keyword.trim())
      await connectJobWs(job_id)
    } catch (err) {
      console.error('[generate] failed:', err)
    }
  }

  return (
    <motion.button
      onClick={handleGenerate}
      disabled={!canGenerate}
      whileTap={{ scale: canGenerate ? 0.97 : 1 }}
      className={[
        'w-full flex items-center justify-center gap-2 rounded-xl py-3.5 text-sm font-semibold transition-all duration-200',
        canGenerate
          ? 'bg-accent hover:bg-accent/90 text-white glow-accent cursor-pointer'
          : isGenerating
            ? 'bg-accent/20 text-accent border border-accent/30 cursor-not-allowed'
            : 'bg-elevated text-muted border border-subtle cursor-not-allowed',
      ].join(' ')}
      aria-label="Generate videos"
    >
      <AnimatePresence mode="wait" initial={false}>
        {isGenerating ? (
          <motion.span
            key="loading"
            initial={{ opacity: 0, scale: 0.8 }}
            animate={{ opacity: 1, scale: 1 }}
            exit={{ opacity: 0, scale: 0.8 }}
            className="flex items-center gap-2"
          >
            <Loader2 size={14} className="animate-spin" />
            Generating…
          </motion.span>
        ) : (
          <motion.span
            key="idle"
            initial={{ opacity: 0, scale: 0.8 }}
            animate={{ opacity: 1, scale: 1 }}
            exit={{ opacity: 0, scale: 0.8 }}
            className="flex items-center gap-2"
          >
            <Zap size={14} />
            Generate
          </motion.span>
        )}
      </AnimatePresence>
    </motion.button>
  )
}
