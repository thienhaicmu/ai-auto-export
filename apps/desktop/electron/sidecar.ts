import { ChildProcess, spawn } from 'child_process'
import net from 'net'
import path from 'path'
import { app } from 'electron'

export class SidecarManager {
  port = 0
  private proc: ChildProcess | null = null

  async start(): Promise<void> {
    this.port = await findFreePort()

    // In dev, __dirname = out/main; backend is 4 levels up from there
    const backendDir = app.isPackaged
      ? path.join(process.resourcesPath, 'backend')
      : path.join(__dirname, '..', '..', '..', '..', 'backend')

    // Support both `python` (Windows default) and `python3` (Unix)
    const pythonExec =
      process.env.PYTHON_EXEC ||
      (process.platform === 'win32' ? 'python' : 'python3')

    console.log(`[sidecar] starting on port ${this.port} cwd=${backendDir}`)

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

    this.proc.stdout?.on('data', (d) => process.stdout.write(`[sidecar] ${d}`))
    this.proc.stderr?.on('data', (d) => process.stderr.write(`[sidecar:err] ${d}`))
    this.proc.on('exit', (code) => {
      console.log(`[sidecar] exited with code ${code}`)
    })

    await waitForHealth(this.port)
    console.log(`[sidecar] ready`)
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
