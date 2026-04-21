"""Lineup Agent handler — build a stage schedule from a list of artists.

This handler is provided for you — no changes needed.

The LlmAgent in server.py calls get_stages() and get_artist_energy() as
FunctionTools to gather context, then calls build_lineup_tool() which
delegates here to produce the final sorted LineupResult.
"""

import json

from pydantic import BaseModel

from shared.config import get_config
from shared.models import ArtistList, LineupSlot
from tools.llm import ask


class LineupResult(BaseModel):
    """A complete festival lineup with stage assignments and reasoning."""

    slots: list[LineupSlot]


async def build_lineup(
    artist_list: ArtistList,
    energy_scores: dict[str, int] | None = None,
) -> LineupResult:
    """Assign artists to stages and time slots, with a reason for each decision.

    Called by build_lineup_tool() in server.py after the LlmAgent has already
    scored each artist's energy via get_artist_energy(). Energy scores inform
    Gemini's placement decisions — highest scorer closes the main stage.

    Args:
        artist_list: The scouted artists to schedule.
        energy_scores: Optional dict mapping artist name to energy score (1–10).

    Returns:
        A LineupResult with one LineupSlot per artist, sorted by time.
    """
    config = get_config()
    scores = energy_scores or {}

    artists_text = "\n".join(
        f"- {a.name} ({a.genre}): {a.description} [energy: {scores.get(a.name, '?')}/10]"
        for a in artist_list.artists
    )
    stages_text = ", ".join(config.stages)

    reply = await ask(
        f"You are programming a {config.vibe!r} festival.\n\n"
        f"Artists (with crowd energy scores):\n{artists_text}\n\n"
        f"Stages: {stages_text}\n\n"
        "Assign each artist a time slot (between 12:00 and 23:00), a stage, "
        "and write one sentence explaining your decision. "
        "Put the highest-energy headliner (highest energy score) in the last slot. "
        "Reply ONLY with a JSON array — no markdown, no explanation:\n"
        '[{"time":"21:00","stage":"Main Stage","artist":"...","genre":"...","reason":"..."},...]',
        system=(
            "You are an expert festival programmer. "
            "Reply with raw JSON only. No markdown code fences, no extra text."
        ),
    )
    clean = reply.strip().removeprefix("```json").removeprefix("```").removesuffix("```").strip()
    data = json.loads(clean)
    slots = [LineupSlot(**s) for s in data]
    slots.sort(key=lambda s: s.time)
    return LineupResult(slots=slots)
