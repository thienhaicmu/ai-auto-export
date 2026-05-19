import { ChildProcess, spawn } from 'child_process'
import fs from 'fs'
import net from 'net'
import path from 'path'
import { app } from 'electron'

export class SidecarManager {
  port = 0
  private proc: ChildProcess | null = null

  async start(): Promise<void> {
    this.port = await findFreePort()

    if (app.isPackaged) {
      await this._startPackaged()
    } else {
      await this._startDev()
    }

    await waitForHealth(this.port)
    console.log(`[sidecar] ready on port ${this.port}`)
  }

  /** Packaged mode: launch the PyInstaller-built sidecar.exe */
  private async _startPackaged(): Promise<void> {
    const resourcesPath = process.resourcesPath

    const sidecarExe = path.join(resourcesPath, 'backend', 'sidecar', 'sidecar.exe')
    if (!fs.existsSync(sidecarExe)) {
      throw new Error(`Backend executable not found: ${sidecarExe}`)
    }

    // userData is writable even in packaged mode (AppData\Roaming\<appName>)
    const userData = app.getPath('userData')

    const env: NodeJS.ProcessEnv = {
      ...process.env,
      PORT: String(this.port),
      // FFmpeg binaries bundled under resources/ffmpeg/
      FFMPEG_DIR: path.join(resourcesPath, 'ffmpeg'),
      // Playwright discovers Chromium by scanning this directory
      PLAYWRIGHT_BROWSERS_PATH: path.join(resourcesPath, 'chromium'),
      // Shared assets (music, fonts, etc.)
      ASSETS_DIR: path.join(resourcesPath, 'assets'),
      // Writable directories in user profile
      APP_TEMP_DIR: path.join(userData, 'temp'),
      APP_LOG_DIR: path.join(userData, 'logs'),
    }

    console.log(`[sidecar] packaged — launching ${sidecarExe} on port ${this.port}`)

    this.proc = spawn(sidecarExe, [String(this.port)], {
      env,
      stdio: 'pipe',
    })

    this._wireStreams()
  }

  /** Dev mode: launch uvicorn via the system Python */
  private async _startDev(): Promise<void> {
    // In dev, __dirname = out/main; backend is 4 levels up from there
    const backendDir = path.join(__dirname, '..', '..', '..', '..', 'backend')

    const pythonExec =
      process.env.PYTHON_EXEC ||
      (process.platform === 'win32' ? 'python' : 'python3')

    console.log(`[sidecar] dev — ${pythonExec} on port ${this.port} cwd=${backendDir}`)

    this.proc = spawn(
      pythonExec,
      [
        '-m', 'uvicorn', 'app.main:app',
        '--host', '127.0.0.1',
        '--port', String(this.port),
        '--log-level', 'info',
      ],
      {
        cwd: backendDir,
        env: { ...process.env, PORT: String(this.port) },
        stdio: 'pipe',
      }
    )

    this._wireStreams()
  }

  private _wireStreams(): void {
    this.proc?.stdout?.on('data', (d) => process.stdout.write(`[sidecar] ${d}`))
    this.proc?.stderr?.on('data', (d) => process.stderr.write(`[sidecar:err] ${d}`))
    this.proc?.on('exit', (code) => {
      console.log(`[sidecar] exited with code ${code}`)
    })
  }

  async stop(): Promise<void> {
    if (this.proc) {
      console.log('[sidecar] stopping')
      this.proc.kill('SIGTERM')
      this.proc = null
    }
  }
}

async function findFreePort(): Promise<number> {
  return new Promise((resolve, reject) => {
    const srv = net.createServer()
    srv.listen(0, '127.0.0.1', () => {
      const { port } = srv.address() as net.AddressInfo
      srv.close(() => resolve(port))
    })
    srv.on('error', reject)
  })
}

async function waitForHealth(port: number, timeoutMs = 30_000): Promise<void> {
  const deadline = Date.now() + timeoutMs
  while (Date.now() < deadline) {
    try {
      const res = await fetch(`http://127.0.0.1:${port}/api/health`)
      if (res.ok) return
    } catch {
      // not ready yet
    }
    await delay(400)
  }
  throw new Error(`Sidecar did not respond within ${timeoutMs}ms`)
}

const delay = (ms: number) => new Promise((r) => setTimeout(r, ms))
