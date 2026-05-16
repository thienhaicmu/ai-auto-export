import uuid
import logging

from fastapi import APIRouter
from pydantic import BaseModel

router = APIRouter()
log = logging.getLogger(__name__)


class IdeaRequest(BaseModel):
    keyword: str


class Idea(BaseModel):
    id: str
    title: str
    angle: str
    hook: str
    estimated_views: str


class IdeasResponse(BaseModel):
    ideas: list[Idea]
    language: str


@router.post("/ideas/generate", response_model=IdeasResponse)
async def generate_ideas(req: IdeaRequest) -> IdeasResponse:
    """Phase 1: returns mock ideas. Phase 2 wires real LLM."""
    kw = req.keyword.strip()
    log.info("Generating mock ideas for keyword: %s", kw)

    ideas = [
        Idea(
            id=uuid.uuid4().hex[:8],
            title=f"{kw.title()} — The Untold Story",
            angle="controversy",
            hook=f"What nobody tells you about {kw}",
            estimated_views="500K–2M",
        ),
        Idea(
            id=uuid.uuid4().hex[:8],
            title=f"The Rise of {kw.title()}",
            angle="timeline",
            hook=f"How {kw} changed everything in 60 seconds",
            estimated_views="200K–800K",
        ),
        Idea(
            id=uuid.uuid4().hex[:8],
            title=f"{kw.title()} Exposed",
            angle="viral hook",
            hook=f"You won't believe what {kw} did next",
            estimated_views="1M–5M",
        ),
    ]

    return IdeasResponse(ideas=ideas, language="en")
