import { FolderOpen } from 'lucide-react'
import { useSetupStore } from '../../store/setupStore'

export function OutputFolderPicker() {
  const outputFolder = useSetupStore((s) => s.outputFolder)
  const setOutputFolder = useSetupStore((s) => s.setOutputFolder)

  async function handlePick() {
    const folder = await window.api.selectFolder()
    if (folder) setOutputFolder(folder)
  }

  const displayPath = outputFolder
    ? outputFolder.length > 38
      ? '…' + outputFolder.slice(-36)
      : outputFolder
    : null

  return (
    <div className="flex flex-col gap-1.5">
      <label className="text-xs font-semibold text-muted uppercase tracking-wider">
        Output Folder
      </label>
      <button
        onClick={handlePick}
        className="flex items-center gap-2 w-full bg-elevated border border-subtle hover:border-accent/50 rounded-lg px-3 py-2.5 text-sm transition-colors group text-left"
        aria-label="Select output folder"
      >
        <FolderOpen
          size={14}
          className="text-muted group-hover:text-accent transition-colors flex-shrink-0"
        />
        <span className={displayPath ? 'text-primary truncate' : 'text-muted'}>
          {displayPath ?? 'Choose folder…'}
        </span>
      </button>
      {!outputFolder && (
        <p className="text-2xs text-muted">
          Videos will save to your selected folder
        </p>
      )}
    </div>
  )
}
