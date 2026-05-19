import { useRef, useEffect } from 'react'
import { motion, AnimatePresence } from 'framer-motion'
import { ExternalLink, Film } from 'lucide-react'
import { usePreviewStore } from '../../store/previewStore'
import { useJobStore } from '../../store/jobStore'
import { useSetupStore } from '../../store/setupStore'

// Convert Windows/Unix absolute path to file:// URL
function toFileUrl(filePath: string): string {
  const fwd = filePath.replace(/\\/g, '/')
  if (/^[A-Za-z]:/.test(fwd)) return `file:///${fwd}`
  return `file://${fwd}`
}

// Map format string to CSS aspect-ratio value
function formatToAspectRatio(format: string): string {
  const map: Record<string, string> = {
    '9:16': '9/16',
    '16:9': '16/9',
    '1:1':  '1/1',
    '3:4':  '3/4',
  }
  return map[format] ?? '9/16'
}

// Platform-aware label for the reveal action
function revealLabel(): string {
  const platform = window.api?.platform ?? 'linux'
  if (platform === 'darwin') return 'Reveal in Finder'
  if (platform === 'win32')  return 'Reveal in Explorer'
  return 'Reveal File'
}

export function VideoPreview() {
  const selectedId = usePreviewStore((s) => s.selectedVariantId)
  const setCurrentTime = usePreviewStore((s) => s.setCurrentTime)
  const selectVariant = usePreviewStore((s) => s.selectVariant)
  const job = useJobStore((s) => s.job)
  const format = useSetupStore((s) => s.format)

  const variant = job?.variants.find((v) => v.variant_id === selectedId)
  const outputPath = variant?.outputPath ?? null

  const videoRef = useRef<HTMLVideoElement>(null)
  const aspectRatio = formatToAspectRatio(format)

  // Auto-select first completed variant
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
              {/* Video container — aspect ratio follows selected format */}
              <div
                className="relative rounded-xl overflow-hidden border border-subtle bg-black shadow-2xl"
                style={{
                  aspectRatio,
                  maxHeight: 'calc(100vh - 220px)',
                  width: 'auto',
                  maxWidth: '100%',
                }}
              >
                <video
                  ref={videoRef}
                  controls
                  autoPlay={false}
                  className="w-full h-full object-contain"
                  onTimeUpdate={(e) => setCurrentTime(e.currentTarget.currentTime)}
                  aria-label="Video preview"
                >
                  <source src={toFileUrl(outputPath)} type="video/mp4" />
                </video>
              </div>

              {/* Actions */}
              <div className="flex items-center gap-2">
                <button
                  onClick={() => window.api.revealFile(outputPath)}
                  className="flex items-center gap-1.5 px-3 py-1.5 bg-elevated border border-subtle rounded-lg text-xs text-secondary hover:text-primary hover:border-accent/50 transition-all"
                >
                  <ExternalLink size={12} />
                  {revealLabel()}
                </button>
                <button
                  onClick={() => window.api.openFile(outputPath)}
                  className="flex items-center gap-1.5 px-3 py-1.5 bg-elevated border border-subtle rounded-lg text-xs text-secondary hover:text-primary hover:border-accent/50 transition-all"
                >
                  <Film size={12} />
                  Open in Player
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
              {/* Placeholder with correct aspect ratio */}
              <div
                className="relative flex items-center justify-center rounded-xl border-2 border-dashed border-subtle bg-elevated/30"
                style={{
                  aspectRatio,
                  maxHeight: 'calc(100vh - 240px)',
                  width: format === '16:9' ? '260px' : '160px',
                }}
              >
                <div className="flex flex-col items-center gap-2">
                  <Film size={28} className="opacity-20" />
                  <span className="text-xs opacity-40">{format}</span>
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
