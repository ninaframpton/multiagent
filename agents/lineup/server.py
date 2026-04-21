"""Lineup Agent — assigns artists to stages and time slots.

Runs on: http://localhost:8002

This is a good example of how ADK FunctionTools work. The LlmAgent has two
tools it can call itself — it decides when to call them, what arguments to pass,
and uses the results to reason about stage placement. You can see these tool
calls in the agent logs when the server is running.

Tools:
    get_stages()              — returns the stage names from config.yaml
    get_artist_energy(name, genre) — rates a single artist's crowd energy 1–10
"""

import uvicorn
from google.adk.a2a.utils.agent_to_a2a import to_a2a
from google.adk.agents import LlmAgent
from google.adk.tools import FunctionTool

from agents.lineup.handler import build_lineup as _build_lineup
from shared.config import get_config
from shared.models import ArtistList
from tools.llm import ask

PORT = 8002


def get_stages() -> str:
    """Return the available festival stage names from config.

    Returns:
        A comma-separated string of stage names, e.g. "Main Stage, Forest Stage, Acoustic Tent".
    """
    config = get_config()
    return ", ".join(config.stages)


async def get_artist_energy(name: str, genre: str) -> int:
    """Rate a single artist's crowd energy on a scale of 1 to 10.

    Higher scores mean more high-energy, headline-worthy acts.
    Use this to decide who should close the main stage.

    Args:
        name: The artist's name, e.g. "Bicep".
        genre: The artist's genre, e.g. "electronic".

    Returns:
        An integer energy score between 1 (mellow) and 10 (peak energy).
    """
    reply = await ask(
        f"Rate the crowd energy of {name!r} ({genre}) at a music festival "
        "on a scale of 1 to 10, where 1 is mellow and 10 is peak energy. "
        "Reply with a single integer only.",
        system="You are a festival programmer. Reply with a single integer only.",
    )
    try:
        return max(1, min(10, int(reply.strip())))
    except ValueError:
        return 5


async def build_lineup_tool(artist_list_json: str, energy_scores_json: str) -> str:
    """Assign artists to festival stages and time slots with reasoning.

    Must be called AFTER get_artist_energy() has been called for every artist.
    Pass the collected scores as a JSON object so placement uses actual energy data.

    Args:
        artist_list_json: A JSON string with an "artists" array where each
            artist has name, genre, and description fields.
        energy_scores_json: A JSON object mapping artist name to energy score,
            e.g. '{"Bicep": 8, "Bon Iver": 4}'.

    Returns:
        A JSON string with a "slots" array. Each slot has time, stage, artist,
        genre, and a reason explaining the placement decision.
    """
    import json

    artist_list = ArtistList.model_validate_json(artist_list_json)
    energy_scores: dict[str, int] = json.loads(energy_scores_json)
    result = await _build_lineup(artist_list, energy_scores=energy_scores)
    return result.model_dump_json()


agent = LlmAgent(
    name="lineup_agent",
    model="gemini-2.0-flash",
    description=(
        "Assigns festival artists to stage time slots. Uses get_stages() to "
        "find available stages and get_artist_energy() to score each act, "
        "then reasons about the best placement for each artist."
    ),
    instruction=(
        "You are an expert festival stage manager. "
        "When given a JSON artist list:\n"
        "1. Call get_stages() to find out what stages are available.\n"
        "2. Call get_artist_energy() for EACH artist individually to score their crowd energy.\n"
        "3. Collect all the scores into a JSON object, e.g. "
        '{\"Artist Name\": 8, \"Other Artist\": 5}.\n'
        "4. Call build_lineup_tool() with both the original artist_list_json AND "
        "the energy_scores_json you just built.\n"
        "Return the JSON output of build_lineup_tool verbatim. "
        "Do not add any extra text or explanation."
    ),
    tools=[
        FunctionTool(func=get_stages),
        FunctionTool(func=get_artist_energy),
        FunctionTool(func=build_lineup_tool),
    ],
)

app = to_a2a(agent, host="localhost", port=PORT)

if __name__ == "__main__":
    uvicorn.run(app, host="0.0.0.0", port=PORT)
