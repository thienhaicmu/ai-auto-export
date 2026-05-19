"""
POST /api/ideas/generate

Phase 2B: calls the configured LLM provider (Gemini or mock) to generate
3 distinct video ideas. Falls back to mock fixture ideas on any error.
"""
import logging
import uuid

from fastapi import APIRouter
from pydantic import BaseModel

from app.models.job import Idea
from app.providers.llm import get_llm_provider
from app.agents import idea_agent
from app.utils.lang import detect_language

router = APIRouter()
log = logging.getLogger(__name__)


class IdeaRequest(BaseModel):
    keyword: str


class IdeasResponse(BaseModel):
    ideas: list[Idea]
    language: str


def _fallback_ideas(keyword: str) -> list[Idea]:
    kw = keyword.strip()
    return [
        Idea(
            id=uuid.uuid4().hex[:8],
            title=f"{kw.title()} — The Untold Story",
            angle="controversy",
            hook=f"What nobody tells you about {kw}",
            estimated_views="500K-2M",
        ),
        Idea(
            id=uuid.uuid4().hex[:8],
            title=f"The Rise of {kw.title()}",
            angle="timeline",
            hook=f"How {kw} changed everything in 60 seconds",
            estimated_views="200K-800K",
        ),
        Idea(
            id=uuid.uuid4().hex[:8],
            title=f"{kw.title()} Exposed",
            angle="viral_hook",
            hook=f"You won't believe what {kw} did next",
            estimated_views="1M-5M",
        ),
    ]


@router.post("/ideas/generate", response_model=IdeasResponse)
async def generate_ideas(req: IdeaRequest) -> IdeasResponse:
    kw = req.keyword.strip()
    log.info("Generating ideas for keyword: %s", kw)

    provider = get_llm_provider()
    ideas, language = await idea_agent.generate_ideas(keyword=kw, provider=provider)

    if not ideas:
        log.info("LLM returned no ideas — using fallback fixture")
        ideas = _fallback_ideas(kw)
        language = detect_language(kw)

    return IdeasResponse(ideas=ideas, language=language)
