import asyncio
import json
import logging

from fastapi import APIRouter, WebSocket, WebSocketDisconnect

from app.services.event_bus import event_bus

router = APIRouter()
log = logging.getLogger(__name__)


@router.websocket("/ws/render/{job_id}")
async def ws_render(websocket: WebSocket, job_id: str) -> None:
    await websocket.accept()
    since_ts = int(websocket.query_params.get("since", 0))
    q = event_bus.subscribe(job_id, since_ts)
    log.info("WS client connected for job %s", job_id)

    try:
        while True:
            try:
                event = await asyncio.wait_for(q.get(), timeout=25.0)
                await websocket.send_text(json.dumps(event))
            except asyncio.TimeoutError:
                # keepalive ping — client ignores this type
                await websocket.send_text(json.dumps({"type": "ping"}))
    except WebSocketDisconnect:
        log.info("WS client disconnected for job %s", job_id)
    except Exception as exc:
        log.error("WS error for job %s: %s", job_id, exc)
    finally:
        event_bus.unsubscribe(job_id, q)
