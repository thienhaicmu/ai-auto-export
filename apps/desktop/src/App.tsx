import { useEffect, useState } from 'react'
import { TitleBar } from './components/ui/TitleBar'
import { LeftSetupPanel } from './components/setup/LeftSetupPanel'
import { PipelineGraph } from './components/pipeline/PipelineGraph'
import { LiveStatus } from './components/status/LiveStatus'
import { StoryboardRail } from './components/storyboard/StoryboardRail'
import { VideoPreview } from './components/storyboard/VideoPreview'
import { checkHealth } from './lib/api'

export default function App() {
  const [backendOnline, setBackendOnline] = useState(false)

  // Poll health until backend is up (sidecar may take a few seconds)
  useEffect(() => {
    let cancelled = false
    async function poll() {
      while (!cancelled) {
        try {
          const h = await checkHealth()
          if (h.ok) { setBackendOnline(true); return }
        } catch {
          // not ready yet
        }
        await new Promise((r) => setTimeout(r, 1500))
      }
    }
    poll()
    return () => { cancelled = true }
  }, [])

  return (
    <div className="flex flex-col h-screen bg-app text-primary overflow-hidden">
      {/* Custom title bar — frameless window */}
      <TitleBar backendOnline={backendOnline} />

      {/* Main content: left panel + center column */}
      <div className="flex flex-1 min-h-0">
        {/* ── Left Setup Panel (360px fixed) ─────────────────────────── */}
        <div className="w-[360px] flex-shrink-0 border-r border-subtle flex flex-col bg-panel min-h-0">
          <LeftSetupPanel />
        </div>

        {/* ── Center Column ───────────────────────────────────────────── */}
        <div className="flex-1 flex flex-col min-w-0 bg-app">
          {/* Pipeline stage graph */}
          <div className="px-5 py-3 border-b border-subtle flex-shrink-0">
            <PipelineGraph />
          </div>

          {/* Live log / status (collapsible, max 240px) */}
          <div className="border-b border-subtle flex-shrink-0">
            <LiveStatus />
          </div>

          {/* Storyboard + Preview fills remaining space */}
          <div className="flex flex-1 min-h-0">
            {/* Scene card rail */}
            <div className="flex-1 border-r border-subtle min-w-0 overflow-hidden">
              <StoryboardRail />
            </div>
            {/* Video preview */}
            <div className="w-[420px] flex-shrink-0 overflow-hidden">
              <VideoPreview />
            </div>
          </div>
        </div>
      </div>
    </div>
  )
}
