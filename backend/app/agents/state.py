"""LangGraph job state. Phase 1: mock adapters only. Phase 2: wire real LLM."""
from typing import TypedDict, Literal, Optional
from app.models.job import Idea, VideoVariantState, JobError


class ResearchOutput(TypedDict, total=False):
    summary: str
    angles: list[str]
    raw: dict


class JobState(TypedDict):
    job_id: str
    keyword: str
    language: str                        # BCP-47 set by LangDetect node
    chosen_idea: Optional[Idea]
    format: Literal["1:1", "3:4", "9:16", "16:9"]
    duration_seconds: int
    output_count: int
    styles: list[str]
    output_folder: str
    research: Optional[ResearchOutput]
    ideas: list[Idea]
    variants: list[VideoVariantState]
    errors: list[JobError]
