"""Orchestrator handler — coordinates the full Scout → Lineup → Hype pipeline.

🔧 TODO: This is the third file you implement (Part 3 of 3).

Your job: call each downstream agent in sequence using call_agent(), then
assemble the results into a FestivalProgram.

The pipeline is:
    vibe (str)
      → Scout  :8001  → ArtistList JSON
      → Lineup :8002  → LineupResult JSON  (slots with reasons)
      → Hype   :8003  → announcement (plain text)
      → FestivalProgram
"""

import logging

from agents.orchestrator.client import call_agent
from agents.lineup.handler import LineupResult
from shared.config import get_config
from shared.models import FestivalProgram

logger = logging.getLogger(__name__)

SCOUT_URL = "http://localhost:8001"
LINEUP_URL = "http://localhost:8002"
HYPE_URL = "http://localhost:8003"


async def run_pipeline(vibe: str) -> FestivalProgram:
    """Run the full multi-agent pipeline for a given festival vibe.

    Call Scout, Lineup, and Hype in sequence via A2A, then assemble
    the FestivalProgram.

    Args:
        vibe: A natural-language vibe string, e.g. "dark techno underground".

    Returns:
        A FestivalProgram with vibe, headline, slots, and announcement.

    Hints:
        - call_agent(url, text) sends a message and returns the text artifact.
        - Each agent's output JSON is the next agent's input text.
        - The headline is the artist in the last slot (sorted by time).
        - config = get_config() gives you the festival name, stages, etc.
    """
    config = get_config()

    logger.info("Running pipeline for %s", vibe)
    artist_json = await call_agent(SCOUT_URL, vibe)
    lineup_json = await call_agent(LINEUP_URL, artist_json)
    announcement = await call_agent(HYPE_URL, lineup_json)

    lineup = LineupResult.model_validate_json(lineup_json)
    headline = lineup.slots[-1].artist if lineup.slots else config.name

    return FestivalProgram(
        vibe=vibe,
        headline=headline,
        slots=lineup.slots,
        announcement=announcement,
    )
