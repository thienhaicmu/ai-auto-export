import asyncio
import json
import sys

async def test_ws():
    try:
        import websockets
        body = json.dumps({"keyword":"karen","format":"9:16","duration_seconds":30,"output_count":1,"styles":["viral"],"output_folder":"C:/Users/6006237/Videos"})
        
        import urllib.request
        req = urllib.request.Request("http://127.0.0.1:8765/api/render/start", data=body.encode(), headers={"Content-Type":"application/json"})
        with urllib.request.urlopen(req) as resp:
            data = json.loads(resp.read())
        job_id = data["job_id"]
        print(f"Started job: {job_id}")
        
        ws_url = f"ws://127.0.0.1:8765/ws/render/{job_id}"
        print(f"Connecting to: {ws_url}")
        
        events = []
        async with websockets.connect(ws_url) as ws:
            print("WebSocket connected!")
            async for msg in ws:
                evt = json.loads(msg)
                print(f"  event: {evt['type']}")
                events.append(evt["type"])
                if evt["type"] in ("job.completed", "job.failed"):
                    break
        
        print(f"\nTotal events received: {len(events)}")
        print("Event types:", events)
        
    except Exception as e:
        print(f"ERROR: {e}", file=sys.stderr)
        raise

asyncio.run(test_ws())
