import { app, BrowserWindow, ipcMain, shell, dialog } from 'electron'
import { join } from 'path'
import { SidecarManager } from './sidecar'

const sidecar = new SidecarManager()
let mainWindow: BrowserWindow | null = null

// ── Window ────────────────────────────────────────────────────────────────

function createWindow(): void {
  mainWindow = new BrowserWindow({
    width: 1440,
    height: 900,
    minWidth: 1280,
    minHeight: 800,
    show: false,
    backgroundColor: '#0A0A0B',
    // Frameless with custom title bar rendered in React
    frame: false,
    titleBarStyle: 'hidden',
    webPreferences: {
      preload: join(__dirname, '../preload/index.js'),
      contextIsolation: true,
      nodeIntegration: false,
      sandbox: false,
    },
  })

  mainWindow.on('ready-to-show', () => {
    mainWindow!.show()
  })

  // Dev: load Vite dev server. Prod: load built renderer.
  const devUrl = process.env.ELECTRON_RENDERER_URL
  if (devUrl) {
    mainWindow.loadURL(devUrl)
    mainWindow.webContents.openDevTools({ mode: 'detach' })
  } else {
    mainWindow.loadFile(join(__dirname, '../renderer/index.html'))
  }
}

// ── IPC handlers ─────────────────────────────────────────────────────────

function registerIpc(): void {
  ipcMain.handle('sidecar:port', () => sidecar.port)

  ipcMain.handle('dialog:selectFolder', async () => {
    if (!mainWindow) return null
    const result = await dialog.showOpenDialog(mainWindow, {
      properties: ['openDirectory', 'createDirectory'],
      title: 'Select Output Folder',
    })
    return result.canceled ? null : result.filePaths[0]
  })

  ipcMain.handle('shell:revealFile', (_evt, filePath: string) => {
    shell.showItemInFolder(filePath)
  })

  ipcMain.handle('shell:openFile', (_evt, filePath: string) => {
    shell.openPath(filePath)
  })

  // Window controls (frameless)
  ipcMain.handle('window:minimize', () => mainWindow?.minimize())
  ipcMain.handle('window:maximize', () => {
    if (mainWindow?.isMaximized()) mainWindow.unmaximize()
    else mainWindow?.maximize()
  })
  ipcMain.handle('window:close', () => mainWindow?.close())
}

// ── Lifecycle ─────────────────────────────────────────────────────────────

app.whenReady().then(async () => {
  try {
    await sidecar.start()
  } catch (err) {
    console.error('[main] sidecar failed to start:', err)
    // In packaged mode, a missing backend exe is a fatal install error.
    if (app.isPackaged) {
      const msg = err instanceof Error ? err.message : String(err)
      await dialog.showMessageBox({
        type: 'error',
        title: 'Backend Failed to Start',
        message: 'The AI Video Factory backend could not be launched.',
        detail: `${msg}\n\nTry reinstalling the application.`,
        buttons: ['Quit'],
      })
      app.quit()
      return
    }
    // Dev mode: continue anyway — developer may run backend separately
  }

  registerIpc()
  createWindow()

  app.on('activate', () => {
    if (BrowserWindow.getAllWindows().length === 0) createWindow()
  })
})

app.on('window-all-closed', async () => {
  await sidecar.stop()
  if (process.platform !== 'darwin') app.quit()
})
