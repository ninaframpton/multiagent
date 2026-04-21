"""Orchestrator Agent — coordinates the full FestBot pipeline.

Runs on: http://localhost:8000

Built with Google ADK (Agent Development Kit). Supports three workflow
orchestration patterns:
- sequential (default): fixed Scout -> Lineup -> Hype pipeline
- parallel: fan-out two Scout branches, merge, then Lineup -> Hype
- loop: iterate Lineup generation until approved (bounded by max iterations)
"""

import os
from typing import AsyncGenerator

import uvicorn
from google.adk.a2a.utils.agent_to_a2a import to_a2a
from google.adk.agents.base_agent import BaseAgent
from google.adk.agents import LlmAgent
from google.adk.agents.loop_agent import LoopAgent
from google.adk.agents.parallel_agent import ParallelAgent
from google.adk.agents.sequential_agent import SequentialAgent
from google.adk.agents.invocation_context import InvocationContext
from google.adk.events import Event, EventActions
from google.adk.tools import FunctionTool

from agents.lineup.handler import LineupResult
from agents.orchestrator.client import call_agent
from shared.config import get_config
from shared.models import Artist, ArtistList, FestivalProgram

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


def expand_vibe_tool(vibe: str) -> str:
    """Create a second scouting vibe for parallel fan-out.

    Args:
        vibe: The original user vibe.

    Returns:
        A broadened vibe string for the second scout branch.
    """
    return f"{vibe}, atmospheric and crossover-friendly"


def merge_artist_lists_tool(primary_json: str, secondary_json: str) -> str:
    """Merge and deduplicate two ArtistList JSON payloads by artist name."""
    primary = ArtistList.model_validate_json(primary_json)
    secondary = ArtistList.model_validate_json(secondary_json)

    merged: list[Artist] = []
    seen: set[str] = set()

    for artist in [*primary.artists, *secondary.artists]:
        key = artist.name.strip().lower()
        if key in seen:
            continue
        seen.add(key)
        merged.append(artist)

    return ArtistList(artists=merged).model_dump_json()


def approve_lineup_tool(lineup_json: str) -> str:
    """Return "true" when lineup has at least three slots; else "false"."""
    try:
        lineup = LineupResult.model_validate_json(lineup_json)
    except Exception:
        return "false"
    return "true" if len(lineup.slots) >= 3 else "false"


class LineupApprovalGate(BaseAgent):
    """Escalate LoopAgent when lineup approval state is true.

    Also copies candidate lineup state into the final lineup key before exit.
    """

    async def _run_async_impl(
        self, ctx: InvocationContext
    ) -> AsyncGenerator[Event, None]:
        approved_raw = str(ctx.session.state.get("lineup_approved", "false"))
        approved = approved_raw.strip().lower() == "true"
        state_delta: dict[str, object] = {}
        if approved:
            candidate = ctx.session.state.get("lineup_json_candidate")
            if candidate:
                state_delta["lineup_json"] = candidate

        yield Event(
            author=self.name,
            actions=EventActions(
                escalate=approved,
                state_delta=state_delta,
            ),
        )


sequential_agent = SequentialAgent(
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


parallel_agent = SequentialAgent(
    name="orchestrator_parallel_workflow",
    description=(
        "Parallel fan-out/fan-in workflow: derive a second vibe, scout both "
        "in parallel, merge artists, then run Lineup and Hype."
    ),
    sub_agents=[
        LlmAgent(
            name="workflow_alt_vibe_step",
            model="gemini-2.0-flash",
            instruction=(
                "Call expand_vibe_tool with the user's original vibe text. "
                "Return only the tool output."
            ),
            tools=[FunctionTool(func=expand_vibe_tool)],
            output_key="alt_vibe",
        ),
        ParallelAgent(
            name="parallel_scout_fanout",
            description="Run two Scout branches concurrently.",
            sub_agents=[
                LlmAgent(
                    name="parallel_scout_primary",
                    model="gemini-2.0-flash",
                    instruction=(
                        "Call scout_step_tool with the user's original vibe "
                        "text and return only the tool output."
                    ),
                    tools=[FunctionTool(func=scout_step_tool)],
                    output_key="scout_primary_json",
                ),
                LlmAgent(
                    name="parallel_scout_alt",
                    model="gemini-2.0-flash",
                    instruction=(
                        "Use alternate vibe from {alt_vibe}. "
                        "Call scout_step_tool(vibe={alt_vibe}) and return "
                        "only the tool output."
                    ),
                    tools=[FunctionTool(func=scout_step_tool)],
                    output_key="scout_alt_json",
                ),
            ],
        ),
        LlmAgent(
            name="parallel_merge_artists_step",
            model="gemini-2.0-flash",
            instruction=(
                "Call merge_artist_lists_tool with primary_json from "
                "{scout_primary_json} and secondary_json from {scout_alt_json}. "
                "Return only the merged artist JSON."
            ),
            tools=[FunctionTool(func=merge_artist_lists_tool)],
            output_key="artist_json",
        ),
        LlmAgent(
            name="parallel_lineup_step",
            model="gemini-2.0-flash",
            instruction=(
                "Use merged artists from {artist_json}. "
                "Call lineup_step_tool(artist_json={artist_json}) and return "
                "only the tool output."
            ),
            tools=[FunctionTool(func=lineup_step_tool)],
            output_key="lineup_json",
        ),
        LlmAgent(
            name="parallel_hype_step",
            model="gemini-2.0-flash",
            instruction=(
                "Use lineup from {lineup_json}. "
                "Call hype_step_tool(lineup_json={lineup_json}) and return only "
                "the tool output."
            ),
            tools=[FunctionTool(func=hype_step_tool)],
            output_key="announcement",
        ),
        LlmAgent(
            name="parallel_assemble_step",
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


loop_lineup_agent = LoopAgent(
    name="loop_lineup_refinement",
    description=(
        "Loop lineup generation and approval until approved or max iterations "
        "is reached."
    ),
    max_iterations=3,
    sub_agents=[
        LlmAgent(
            name="loop_lineup_candidate_step",
            model="gemini-2.0-flash",
            instruction=(
                "Call lineup_step_tool using artists from {artist_json}. "
                "Return only the lineup JSON."
            ),
            tools=[FunctionTool(func=lineup_step_tool)],
            output_key="lineup_json_candidate",
        ),
        LlmAgent(
            name="loop_lineup_approval_step",
            model="gemini-2.0-flash",
            instruction=(
                "Call approve_lineup_tool with {lineup_json_candidate}. "
                "Return only true or false."
            ),
            tools=[FunctionTool(func=approve_lineup_tool)],
            output_key="lineup_approved",
        ),
        LineupApprovalGate(name="loop_lineup_gate"),
    ],
)


loop_agent = SequentialAgent(
    name="orchestrator_loop_workflow",
    description=(
        "Loop refinement workflow: Scout -> lineup loop -> Hype -> assemble."
    ),
    sub_agents=[
        LlmAgent(
            name="loop_scout_step",
            model="gemini-2.0-flash",
            instruction=(
                "Call scout_step_tool with the user's vibe text exactly as-is. "
                "Return only the tool output."
            ),
            tools=[FunctionTool(func=scout_step_tool)],
            output_key="artist_json",
        ),
        loop_lineup_agent,
        LlmAgent(
            name="loop_hype_step",
            model="gemini-2.0-flash",
            instruction=(
                "Use final lineup from {lineup_json}. "
                "Call hype_step_tool(lineup_json={lineup_json}) and return only "
                "the tool output."
            ),
            tools=[FunctionTool(func=hype_step_tool)],
            output_key="announcement",
        ),
        LlmAgent(
            name="loop_assemble_step",
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


WORKFLOW_TYPE = os.getenv("ORCHESTRATOR_WORKFLOW_TYPE", "sequential").lower()

_WORKFLOW_AGENTS = {
    "sequential": sequential_agent,
    "parallel": parallel_agent,
    "loop": loop_agent,
}

agent = _WORKFLOW_AGENTS.get(WORKFLOW_TYPE, sequential_agent)

app = to_a2a(agent, host="localhost", port=PORT)

if __name__ == "__main__":
    uvicorn.run(app, host="0.0.0.0", port=PORT)
