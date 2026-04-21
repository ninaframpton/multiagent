"""Orchestrator Agent — coordinates the full FestBot pipeline.

Runs on: http://localhost:8000

Built with Google ADK (Agent Development Kit). A SequentialAgent coordinates
Scout -> Lineup -> Hype workflow steps and returns the final festival program.
"""

import uvicorn
from google.adk.a2a.utils.agent_to_a2a import to_a2a
from google.adk.agents import LlmAgent
from google.adk.agents.sequential_agent import SequentialAgent
from google.adk.tools import FunctionTool

from agents.lineup.handler import LineupResult
from agents.orchestrator.client import call_agent
from shared.config import get_config
from shared.models import FestivalProgram

PORT = 8000
SCOUT_URL = "http://localhost:8001"
LINEUP_URL = "http://localhost:8002"
HYPE_URL = "http://localhost:8003"


async def scout_step_tool(vibe: str) -> str:
    """Call Scout and return its artist-list JSON artifact."""
    return await call_agent(SCOUT_URL, vibe)


async def lineup_step_tool(artist_json: str) -> str:
    """Call Lineup and return its lineup JSON artifact."""
    return await call_agent(LINEUP_URL, artist_json)


async def hype_step_tool(lineup_json: str) -> str:
    """Call Hype and return the final announcement text artifact."""
    return await call_agent(HYPE_URL, lineup_json)


def assemble_program_tool(vibe: str, lineup_json: str, announcement: str) -> str:
    """Assemble the final FestivalProgram JSON from workflow step outputs."""
    config = get_config()
    lineup = LineupResult.model_validate_json(lineup_json)
    headline = lineup.slots[-1].artist if lineup.slots else config.name
    program = FestivalProgram(
        vibe=vibe,
        headline=headline,
        slots=lineup.slots,
        announcement=announcement,
    )
    return program.model_dump_json(indent=2)


agent = SequentialAgent(
    name="orchestrator_workflow",
    description=(
        "Deterministic ADK workflow orchestrator that executes Scout, Lineup, "
        "Hype, then final assembly in sequence."
    ),
    sub_agents=[
        LlmAgent(
            name="workflow_scout_step",
            model="gemini-2.0-flash",
            instruction=(
                "Call scout_step_tool with the user's vibe text exactly as-is. "
                "Return only the tool output."
            ),
            tools=[FunctionTool(func=scout_step_tool)],
            output_key="artist_json",
        ),
        LlmAgent(
            name="workflow_lineup_step",
            model="gemini-2.0-flash",
            instruction=(
                "Use the prior step output stored in {artist_json}. "
                "Call lineup_step_tool(artist_json={artist_json}) and return only "
                "the tool output."
            ),
            tools=[FunctionTool(func=lineup_step_tool)],
            output_key="lineup_json",
        ),
        LlmAgent(
            name="workflow_hype_step",
            model="gemini-2.0-flash",
            instruction=(
                "Use the prior step output stored in {lineup_json}. "
                "Call hype_step_tool(lineup_json={lineup_json}) and return only "
                "the tool output."
            ),
            tools=[FunctionTool(func=hype_step_tool)],
            output_key="announcement",
        ),
        LlmAgent(
            name="workflow_assemble_step",
            model="gemini-2.0-flash",
            instruction=(
                "Call assemble_program_tool using the original user vibe text, "
                "lineup_json from {lineup_json}, and announcement from "
                "{announcement}. Return only the final program JSON."
            ),
            tools=[FunctionTool(func=assemble_program_tool)],
        ),
    ],
)

app = to_a2a(agent, host="localhost", port=PORT)

if __name__ == "__main__":
    uvicorn.run(app, host="0.0.0.0", port=PORT)
