import { useRef, useEffect } from 'react'
import { motion, AnimatePresence } from 'framer-motion'
import { Play, ExternalLink, Film } from 'lucide-react'
import { usePreviewStore } from '../../store/previewStore'
import { useJobStore } from '../../store/jobStore'

export function VideoPreview() {
  const selectedId = usePreviewStore((s) => s.selectedVariantId)
  const setCurrentTime = usePreviewStore((s) => s.setCurrentTime)
  const job = useJobStore((s) => s.job)

  const variant = job?.variants.find((v) => v.variant_id === selectedId)
  const outputPath = variant?.outputPath ?? null

  const videoRef = useRef<HTMLVideoElement>(null)

  // Auto-select first completed variant
  const selectVariant = usePreviewStore((s) => s.selectVariant)
  useEffect(() => {
    if (!selectedId && job) {
      const done = job.variants.find((v) => v.status === 'done')
      if (done) selectVariant(done.variant_id)
    }
  }, [job?.variants, selectedId, selectVariant])

  // Reload video when outputPath changes
  useEffect(() => {
    if (videoRef.current && outputPath) {
      videoRef.current.load()
    }
  }, [outputPath])

  return (
    <div className="flex flex-col h-full bg-app">
      <div className="px-4 py-2 border-b border-subtle flex-shrink-0">
        <span className="text-xs font-semibold text-muted uppercase tracking-wider">
          Preview
        </span>
      </div>

      <div className="flex-1 flex items-center justify-center p-4">
        <AnimatePresence mode="wait">
          {outputPath ? (
            <motion.div
              key={outputPath}
              initial={{ opacity: 0, scale: 0.96 }}
              animate={{ opacity: 1, scale: 1 }}
              exit={{ opacity: 0, scale: 0.96 }}
              transition={{ duration: 0.28, ease: [0.22, 1, 0.36, 1] }}
              className="relative flex flex-col items-center gap-3 w-full"
            >
              {/* 9:16 video container */}
              <div
                className="relative rounded-xl overflow-hidden border border-subtle bg-black shadow-2xl"
                style={{ aspectRatio: '9/16', maxHeight: 'calc(100vh - 220px)', width: 'auto' }}
              >
                <video
                  ref={videoRef}
                  controls
                  autoPlay={false}
                  className="w-full h-full object-contain"
                  onTimeUpdate={(e) => setCurrentTime(e.currentTarget.currentTime)}
                  aria-label="Video preview"
                >
                  {/* file:// path works in Electron renderer */}
                  <source src={`file://${outputPath}`} type="video/mp4" />
                </video>
              </div>

              {/* Actions */}
              <div className="flex items-center gap-2">
                <button
                  onClick={() => window.api.revealFile(outputPath)}
                  className="flex items-center gap-1.5 px-3 py-1.5 bg-elevated border border-subtle rounded-lg text-xs text-secondary hover:text-primary hover:border-accent/50 transition-all"
                >
                  <ExternalLink size={12} />
                  Reveal in Finder
                </button>
              </div>
            </motion.div>
          ) : (
            <motion.div
              key="empty"
              initial={{ opacity: 0 }}
              animate={{ opacity: 1 }}
              className="flex flex-col items-center gap-4 text-muted"
            >
              {/* 9:16 placeholder */}
              <div
                className="relative flex items-center justify-center rounded-xl border-2 border-dashed border-subtle bg-elevated/30"
                style={{ aspectRatio: '9/16', maxHeight: 'calc(100vh - 240px)', width: '200px' }}
              >
                <div className="flex flex-col items-center gap-2">
                  <Film size={28} className="opacity-20" />
                  <span className="text-xs opacity-40">9:16</span>
                </div>
              </div>
              <p className="text-xs text-center max-w-[180px]">
                {job?.status === 'running'
                  ? 'Video will appear here when ready'
                  : 'Generate a video to preview it here'}
              </p>
            </motion.div>
          )}
        </AnimatePresence>
      </div>
    </div>
  )
}
