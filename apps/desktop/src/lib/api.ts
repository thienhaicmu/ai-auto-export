import type { HealthStatus, Idea, JobSnapshot } from './types'

let _port: number | null = null

async function port(): Promise<number> {
  if (_port !== null) return _port
  _port = await window.api.getSidecarPort()
  return _port
}

async function get(path: string): Promise<Response> {
  const p = await port()
  return fetch(`http://127.0.0.1:${p}${path}`)
}

async function post(path: string, body: unknown): Promise<Response> {
  const p = await port()
  return fetch(`http://127.0.0.1:${p}${path}`, {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify(body),
  })
}

export async function checkHealth(): Promise<HealthStatus> {
  const res = await get('/api/health')
  if (!res.ok) throw new Error('Health check failed')
  return res.json()
}

export async function generateIdeas(keyword: string): Promise<{ ideas: Idea[]; language: string }> {
  const res = await post('/api/ideas/generate', { keyword })
  if (!res.ok) throw new Error('Ideas generation failed')
  return res.json()
}

export interface RenderRequest {
  keyword: string
  format: string
  duration_seconds: number
  output_count: number
  styles: string[]
  output_folder: string
  quality_mode: 'preview' | 'final'
  chosen_idea_id?: string
}

export async function startRender(req: RenderRequest): Promise<{ job_id: string }> {
  const res = await post('/api/render/start', req)
  if (!res.ok) throw new Error('Render start failed')
  return res.json()
}

export async function getJob(jobId: string): Promise<JobSnapshot> {
  const res = await get(`/api/render/jobs/${jobId}`)
  if (!res.ok) throw new Error('Get job failed')
  return res.json()
}

export async function cancelJob(jobId: string): Promise<void> {
  await post(`/api/render/jobs/${jobId}/cancel`, {})
}

export async function getWsUrl(jobId: string, sinceTs = 0): Promise<string> {
  const p = await port()
  return `ws://127.0.0.1:${p}/ws/render/${jobId}?since=${sinceTs}`
}
