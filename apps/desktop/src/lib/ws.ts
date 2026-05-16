import { getWsUrl } from './api'
import { useJobStore } from '../store/jobStore'
import type { WsEvent } from './types'

let socket: WebSocket | null = null
let activeJobId: string | null = null
let lastTs = 0
let reconnectTimer: ReturnType<typeof setTimeout> | null = null

export async function connectJobWs(jobId: string): Promise<void> {
  disconnectJobWs()
  activeJobId = jobId
  lastTs = 0
  await openSocket(jobId)
}

export function disconnectJobWs(): void {
  activeJobId = null
  if (reconnectTimer) {
    clearTimeout(reconnectTimer)
    reconnectTimer = null
  }
  if (socket) {
    socket.onclose = null // prevent reconnect loop
    socket.close()
    socket = null
  }
}

async function openSocket(jobId: string): Promise<void> {
  try {
    const url = await getWsUrl(jobId, lastTs)
    socket = new WebSocket(url)

    socket.onmessage = (e) => {
      try {
        const event: WsEvent = JSON.parse(e.data as string)
        if (event.type === 'ping') return
        if (event.ts) lastTs = Math.max(lastTs, event.ts)
        useJobStore.getState().applyEvent(event)
      } catch {
        // ignore malformed frames
      }
    }

    socket.onerror = (e) => {
      console.warn('[ws] error', e)
    }

    socket.onclose = () => {
      socket = null
      // Reconnect only if this job is still active
      if (activeJobId === jobId) {
        reconnectTimer = setTimeout(() => openSocket(jobId), 2000)
      }
    }
  } catch (err) {
    console.error('[ws] failed to open:', err)
  }
}
