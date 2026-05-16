import pytest
from httpx import AsyncClient, ASGITransport
from app.main import app


@pytest.mark.asyncio
async def test_health_returns_200():
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
        resp = await client.get("/api/health")
    assert resp.status_code == 200
    body = resp.json()
    assert body["ok"] is True
    assert "version" in body
    assert "ffmpeg" in body


@pytest.mark.asyncio
async def test_ideas_generate():
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
        resp = await client.post("/api/ideas/generate", json={"keyword": "karen"})
    assert resp.status_code == 200
    body = resp.json()
    assert len(body["ideas"]) > 0


@pytest.mark.asyncio
async def test_render_start():
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
        resp = await client.post("/api/render/start", json={
            "keyword": "karen",
            "format": "9:16",
            "duration_seconds": 30,
            "output_count": 1,
            "styles": ["viral"],
            "output_folder": "output",
        })
    assert resp.status_code == 200
    body = resp.json()
    assert body["job_id"].startswith("job_")
