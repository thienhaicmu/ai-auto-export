import { motion, AnimatePresence } from 'framer-motion'
import { Zap, Loader2, AlertCircle } from 'lucide-react'
import { useState } from 'react'
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
  const qualityMode = useSetupStore((s) => s.qualityMode)
  const selectedIdeaId = useSetupStore((s) => s.selectedIdeaId)

  const isGenerating = useJobStore((s) => s.isGenerating)
  const startJob = useJobStore((s) => s.startJob)
  const reset = useJobStore((s) => s.reset)
  const clearPreview = usePreviewStore((s) => s.clear)

  const [validationError, setValidationError] = useState<string | null>(null)

  // Validation
  function validate(): string | null {
    if (!keyword.trim()) return 'Enter a keyword to continue'
    if (durationSeconds < 5 || durationSeconds > 300) return 'Duration must be 5–300 seconds'
    if (outputCount < 1 || outputCount > 10) return 'Output count must be 1–10'
    if (styles.length === 0) return 'Select at least one style'
    return null
  }

  const canGenerate = keyword.trim().length > 0 && !isGenerating

  async function handleGenerate() {
    const err = validate()
    if (err) { setValidationError(err); return }
    setValidationError(null)

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
        quality_mode: qualityMode,
        chosen_idea_id: selectedIdeaId ?? undefined,
      })
      startJob(job_id, keyword.trim())
      await connectJobWs(job_id)
    } catch (err) {
      console.error('[generate] failed:', err)
      setValidationError('Failed to start render. Is the backend running?')
    }
  }

  return (
    <div className="flex flex-col gap-2">
      {/* Validation error */}
      <AnimatePresence>
        {validationError && (
          <motion.div
            initial={{ opacity: 0, y: -4 }}
            animate={{ opacity: 1, y: 0 }}
            exit={{ opacity: 0, y: -4 }}
            className="flex items-center gap-1.5 px-3 py-2 bg-error/10 border border-error/30 rounded-lg text-xs text-error"
          >
            <AlertCircle size={12} className="flex-shrink-0" />
            {validationError}
          </motion.div>
        )}
      </AnimatePresence>

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
    </div>
  )
}
