"""
Phase 1 stub: mock LangGraph pipeline.
Returns a fixture timeline for the viral template.
Phase 2 wires real nodes with Gemini adapter.
"""
import logging
from app.agents.state import JobState

log = logging.getLogger(__name__)


async def run_pipeline(state: JobState) -> JobState:
    """Run the full agent pipeline (mock for Phase 1)."""
    log.info("Mock pipeline running for job %s keyword='%s'", state["job_id"], state["keyword"])

    state["language"] = "en"
    state["research"] = {
        "summary": f"Mock research for '{state['keyword']}'",
        "angles": ["controversy", "timeline", "viral hook"],
    }

    return state
