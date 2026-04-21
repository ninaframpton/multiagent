"""Scout Agent — discovers artists for a given festival vibe.

Runs on: http://localhost:8001

Built with Google ADK (Agent Development Kit). The LlmAgent receives a vibe
string via A2A, calls the scout_artists tool, and returns the JSON result.
"""

import uvicorn
from google.adk.agents import LlmAgent
from google.adk.a2a.utils.agent_to_a2a import to_a2a
from google.adk.tools import FunctionTool

from agents.scout.handler import scout_artists as _scout_artists
from shared.config import get_config

PORT = 8001


async def scout_artists_tool(vibe: str) -> str:
    """Scout 5 real artists for the given festival vibe and return them as JSON.

    Fetches real artist names from Last.fm using the genre in config.yaml,
    then asks Gemini to write a festival description for each one.

    Args:
        vibe: A natural-language festival vibe string.

    Returns:
        A JSON string containing an array of artists with name, genre, and
        description fields.
    """
    config = get_config()
    result = await _scout_artists(vibe, genre=config.genre)
    return result.model_dump_json()


agent = LlmAgent(
    name="scout_agent",
    model="gemini-2.0-flash",
    description="Scouts and returns a list of artists suited to a festival vibe.",
    instruction=(
        "You are a music curator for festivals. "
        "When given a festival vibe, call the scout_artists_tool and return "
        "its JSON output verbatim. Do not add any extra text or explanation."
    ),
    tools=[FunctionTool(func=scout_artists_tool)],
)

app = to_a2a(agent, host="localhost", port=PORT)

if __name__ == "__main__":
    uvicorn.run(app, host="0.0.0.0", port=PORT)
