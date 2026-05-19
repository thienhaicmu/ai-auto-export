from typing import Literal, Optional
from pydantic import BaseModel, Field


class Idea(BaseModel):
    id: str
    title: str
    angle: str
    hook: str
    estimated_views: str


class VisualDirection(BaseModel):
    energy_level: int = 3                          # 1–5
    motion_intensity: Literal["calm", "medium", "high", "impact"] = "medium"
    layout_mode: Literal["center", "lower_third", "split", "full_bleed"] = "center"
    transition_style: Literal["cut", "zoom", "flash", "glitch"] = "cut"
    emphasis_words: list[str] = Field(default_factory=list)
    background_treatment: Literal["gradient", "blurred_image", "dark_image", "abstract"] = "gradient"
    subtitle_emphasis: bool = False
    pacing_note: str = ""


class SceneProps(BaseModel):
    headline: str
    subhead: str = ""
    background_image: Optional[str] = None
    highlight_word_indices: list[int] = Field(default_factory=list)
    animation_seed: int = 0
    accent_color: str = "#7C5CFF"
    visual_direction: Optional[VisualDirection] = None


class Scene(BaseModel):
    index: int
    start: float
    end: float
    template: str
    role: str = ""        # hook | context | escalation | twist | payoff
    props: SceneProps


class AudioDirection(BaseModel):
    """
    Cinematic audio direction data attached to an AudioConfig.

    All fields are optional with safe defaults so that existing timelines
    that lack this object continue to render without change.
    """
    bpm: int = 128
    beat_markers: list[float] = Field(default_factory=list)  # seconds from video start
    intro_hit: Optional[float] = None    # time of first strong beat (seconds)
    transition_hits: list[float] = Field(default_factory=list)  # scene-boundary beats
    outro_hit: Optional[float] = None   # last strong beat before end
    fade_in_ms: int = 500               # music fade-in duration
    fade_out_ms: int = 1000             # music fade-out duration
    duck_voice: bool = True             # duck music when voice is present
    scene_energy: list[int] = Field(default_factory=list)   # per-scene energy 1–5


class AudioConfig(BaseModel):
    voice_track: Optional[str] = None
    music_bed: Optional[str] = None
    music_gain_db: float = -22.0
    direction: Optional[AudioDirection] = None   # Phase 4A; None = legacy behaviour


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
    quality_mode: Literal["preview", "final"] = "final"
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
    recoverable: bool = False
    detail: Optional[str] = None   # safe for internal logs; never exposed to browser
