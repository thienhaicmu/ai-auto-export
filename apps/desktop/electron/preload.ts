import { contextBridge, ipcRenderer } from 'electron'

// Narrow bridge — only what the renderer needs. No broad Node access.
const api = {
  getSidecarPort: (): Promise<number> =>
    ipcRenderer.invoke('sidecar:port'),

  selectFolder: (): Promise<string | null> =>
    ipcRenderer.invoke('dialog:selectFolder'),

  revealFile: (filePath: string): Promise<void> =>
    ipcRenderer.invoke('shell:revealFile', filePath),

  openFile: (filePath: string): Promise<void> =>
    ipcRenderer.invoke('shell:openFile', filePath),

  // Window controls for frameless window
  minimizeWindow: (): Promise<void> => ipcRenderer.invoke('window:minimize'),
  maximizeWindow: (): Promise<void> => ipcRenderer.invoke('window:maximize'),
  closeWindow: (): Promise<void> => ipcRenderer.invoke('window:close'),

  platform: process.platform as NodeJS.Platform,
}

contextBridge.exposeInMainWorld('api', api)

export type WindowApi = typeof api
