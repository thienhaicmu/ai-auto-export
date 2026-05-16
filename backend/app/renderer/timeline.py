"""
Timeline JSON schema — contract between agents and renderer.
Both sides are Pydantic v2 models.
"""
from app.models.job import Timeline, Scene, SceneProps, AudioConfig, SubtitleConfig

__all__ = ["Timeline", "Scene", "SceneProps", "AudioConfig", "SubtitleConfig"]


def fixture_timeline(
    job_id: str,
    keyword: str,
    output_path: str,
    duration_seconds: int = 30,
) -> Timeline:
    """Phase 1: returns a hardcoded 5-scene viral timeline for smoke-testing."""
    scenes = [
        Scene(
            index=i,
            start=i * (duration_seconds / 5),
            end=(i + 1) * (duration_seconds / 5),
            template="viral",
            props=SceneProps(
                headline=headlines[i],
                subhead=subheads[i],
                animation_seed=1000 + i * 37,
            ),
        )
        for i in range(5)
    ]

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

    for i, scene in enumerate(scenes):
        scene.props.headline = headlines[i]
        scene.props.subhead = subheads[i]

    return Timeline(
        job_id=job_id,
        variant_id="v01",
        language="en",
        style="viral",
        format="9:16",
        resolution=(1080, 1920),
        fps=30,
        duration_seconds=duration_seconds,
        audio=AudioConfig(
            music_bed="assets/music/viral_pulse.mp3",
            music_gain_db=-22,
        ),
        subtitles=SubtitleConfig(style="viral_bold"),
        scenes=scenes,
        output_path=output_path,
    )
