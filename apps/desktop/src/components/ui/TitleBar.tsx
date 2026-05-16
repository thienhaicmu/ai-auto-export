import { Minus, Square, X } from 'lucide-react'

export function TitleBar({ backendOnline }: { backendOnline: boolean }) {
  return (
    <div className="h-10 flex items-center px-4 border-b border-subtle app-drag flex-shrink-0 bg-panel">
      {/* App identity */}
      <div className="flex items-center gap-2 app-no-drag">
        <div className="w-5 h-5 rounded bg-accent flex items-center justify-center">
          <span className="text-[9px] font-black text-white">AI</span>
        </div>
        <span className="text-sm font-semibold text-primary tracking-tight">
          AI Keyword Video Factory
        </span>
        <span className="text-xs text-muted">v0.1</span>
      </div>

      {/* Backend status indicator */}
      <div className="flex items-center gap-1.5 ml-3">
        <div
          className={`w-1.5 h-1.5 rounded-full transition-colors duration-300 ${
            backendOnline ? 'bg-success' : 'bg-warn animate-pulse'
          }`}
        />
        <span className="text-2xs text-muted tabular">
          {backendOnline ? 'backend ready' : 'connecting…'}
        </span>
      </div>

      {/* Spacer (draggable) */}
      <div className="flex-1" />

      {/* Window controls */}
      <div className="flex items-center gap-0.5 app-no-drag">
        <button
          onClick={() => window.api.minimizeWindow()}
          className="w-8 h-8 flex items-center justify-center text-muted hover:text-primary hover:bg-elevated rounded transition-colors"
          aria-label="Minimize"
        >
          <Minus size={13} />
        </button>
        <button
          onClick={() => window.api.maximizeWindow()}
          className="w-8 h-8 flex items-center justify-center text-muted hover:text-primary hover:bg-elevated rounded transition-colors"
          aria-label="Maximize"
        >
          <Square size={11} />
        </button>
        <button
          onClick={() => window.api.closeWindow()}
          className="w-8 h-8 flex items-center justify-center text-muted hover:text-error hover:bg-error/10 rounded transition-colors"
          aria-label="Close"
        >
          <X size={13} />
        </button>
      </div>
    </div>
  )
}
