from typing import Literal, Optional
from pydantic import BaseModel, Field


class Idea(BaseModel):
    id: str
    title: str
    angle: str
    hook: str
    estimated_views: str


class SceneProps(BaseModel):
    headline: str
    subhead: str = ""
    background_image: Optional[str] = None
    highlight_word_indices: list[int] = Field(default_factory=list)
    animation_seed: int = 0
    accent_color: str = "#7C5CFF"


class Scene(BaseModel):
    index: int
    start: float
    end: float
    template: str
    props: SceneProps


class AudioConfig(BaseModel):
    voice_track: Optional[str] = None
    music_bed: Optional[str] = None
    music_gain_db: float = -22.0


class SubtitleConfig(BaseModel):
    path: Optional[str] = None
    style: str = "viral_bold"


class Timeline(BaseModel):
    version: int = 1
    job_id: str
    variant_id: str
    language: str = "en"
    style: str = "viral"
    format: str = "9:16"
    resolution: tuple[int, int] = (1080, 1920)
    fps: int = 30
    duration_seconds: int
    audio: AudioConfig = Field(default_factory=AudioConfig)
    subtitles: SubtitleConfig = Field(default_factory=SubtitleConfig)
    scenes: list[Scene] = Field(default_factory=list)
    output_path: str


class VideoVariantState(BaseModel):
    variant_id: str
    style: str = "viral"
    status: Literal["pending", "running", "done", "error"] = "pending"
    progress: float = 0.0
    timeline: Optional[Timeline] = None
    output_path: Optional[str] = None
    error: Optional[str] = None


class JobError(BaseModel):
    stage: str
    message: str
    variant_id: Optional[str] = None
