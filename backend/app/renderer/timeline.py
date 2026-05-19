"""
Timeline JSON schema — contract between agents and renderer.
Both sides are Pydantic v2 models.
"""
from app.models.job import Timeline, Scene, SceneProps, AudioConfig, SubtitleConfig

__all__ = ["Timeline", "Scene", "SceneProps", "AudioConfig", "SubtitleConfig"]


_QUALITY_PRESETS: dict[str, dict] = {
    "preview": {"resolution": (480, 854),  "fps": 24},
    "final":   {"resolution": (1080, 1920), "fps": 30},
}


def fixture_timeline(
    job_id: str,
    keyword: str,
    output_path: str,
    duration_seconds: int = 30,
    quality_mode: str = "final",
) -> Timeline:
    """Phase 1: returns a hardcoded 5-scene viral timeline for smoke-testing."""
    preset = _QUALITY_PRESETS.get(quality_mode, _QUALITY_PRESETS["final"])
    resolution = preset["resolution"]
    fps = preset["fps"]

    headlines = [
        keyword.upper(),
        "WHAT THEY",
        "DON'T WANT",
        "YOU TO KNOW",
        "FIND OUT NOW",
    ]
    subheads = [
        "The untold story",
        "Hidden for years",
        "Exposed at last",
        "The real truth",
        "Watch till the end",
    ]

    scene_dur = duration_seconds / 5
    scenes = [
        Scene(
            index=i,
            start=i * scene_dur,
            end=(i + 1) * scene_dur,
            template="viral",
            props=SceneProps(
                headline=headlines[i],
                subhead=subheads[i],
                animation_seed=1000 + i * 37,
                highlight_word_indices=[0] if i == 0 else [],
            ),
        )
        for i in range(5)
    ]

    return Timeline(
        job_id=job_id,
        variant_id="v01",
        language="en",
        style="viral",
        format="9:16",
        quality_mode=quality_mode,
        resolution=resolution,
        fps=fps,
        duration_seconds=duration_seconds,
        audio=AudioConfig(
            music_bed=None,
            music_gain_db=-22.0,
        ),
        subtitles=SubtitleConfig(style="viral_bold"),
        scenes=scenes,
        output_path=output_path,
    )
