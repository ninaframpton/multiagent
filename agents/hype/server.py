"""Hype Agent — writes a crowd announcement for the festival lineup.

Runs on: http://localhost:8003

🔧 TODO: This is the second file you implement (Part 2 of 3).

Follow the same pattern as agents/lineup/server.py. The Lineup server is a
good reference — notice how it gives the LlmAgent multiple FunctionTools and
the agent decides when to call each one.

Your Hype agent needs two tools:
    1. get_festival_name  — already implemented in handler.py, just wrap it
    2. write_announcement — the function you implement in handler.py

Steps:
    1. Write a tool function for each (wrap the handler functions)
    2. Create an LlmAgent with both tools and an instruction that tells it
       to call get_festival_name first, then write_announcement
    3. Call to_a2a() to produce the Starlette app

Once done, verify your agent card appears at:
    curl http://localhost:8003/.well-known/agent-card.json
"""

import uvicorn
from google.adk.a2a.utils.agent_to_a2a import to_a2a
from google.adk.agents import LlmAgent
from google.adk.tools import FunctionTool

from agents.hype.handler import get_festival_name as _get_festival_name
from agents.hype.handler import write_announcement as _write_announcement

PORT = 8003

# ── Step 1: write tool functions ──────────────────────────────────────────────
#
# def get_festival_name_tool() -> str:
#     """Return the festival name."""
#     return _get_festival_name()
#
# async def write_announcement_tool(lineup_json: str) -> str:
#     """Write a crowd announcement for the given lineup JSON."""
#     ...


# ── Step 2: create the LlmAgent ───────────────────────────────────────────────
#
# agent = LlmAgent(
#     name="hype_agent",
#     model="gemini-2.0-flash",
#     description="...",
#     instruction=(
#         "You are a festival MC. "
#         "First call get_festival_name_tool() to find the festival name. "
#         "Then call write_announcement_tool() with the lineup JSON you received. "
#         "Return the announcement text verbatim."
#     ),
#     tools=[
#         FunctionTool(func=get_festival_name_tool),
#         FunctionTool(func=write_announcement_tool),
#     ],
# )


# ── Step 3: build the A2A app ─────────────────────────────────────────────────
#
# app = to_a2a(agent, host="localhost", port=PORT)


# Delete this line once you have defined `app` above:
raise NotImplementedError("Implement agents/hype/server.py — see TASK.md")


if __name__ == "__main__":
    uvicorn.run(app, host="0.0.0.0", port=PORT)
