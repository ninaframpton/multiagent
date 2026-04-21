"""FestBot demo — run the end-to-end multi-agent pipeline.

Usage:
    uv run python main.py [vibe]

Example:
    uv run python main.py "dark techno underground"
"""

import asyncio
import json
import logging
import sys

from agents.orchestrator.client import call_agent
from shared.config import get_config

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s  %(name)s  %(levelname)s  %(message)s",
)

ORCHESTRATOR_URL = "http://localhost:8000"


def build_poster_prompt(program: dict, config_name: str) -> str:
    """Build an image-generation prompt from the festival program.

    Args:
        program: The FestivalProgram as a plain dict.
        config_name: Festival name from config.yaml.

    Returns:
        A detailed prompt ready to paste into any image AI.
    """
    headline = program.get("headline", "unknown artist")
    vibe = program.get("vibe", "music festival")
    slots = program.get("slots", [])
    genres = ", ".join({s["genre"] for s in slots if s.get("genre")}) or vibe

    return (
        f"Vintage music festival poster for '{config_name}'. "
        f"Headline act: {headline}. "
        f"Festival vibe: {vibe}. "
        f"Genres on the bill: {genres}. "
        "Bold retro typography, psychedelic illustration, stage silhouettes, "
        "crowd energy, dramatic concert lighting, sun setting behind the stage. "
        "Screen-print style with a limited colour palette. "
        "High detail, vibrant, iconic festival art."
    )


async def main() -> None:
    """Send a vibe to the Orchestrator and pretty-print the festival program."""
    config = get_config()
    vibe = " ".join(sys.argv[1:]) if len(sys.argv) > 1 else config.vibe

    print(f"\n🎪  FestBot — curating a lineup for: {vibe!r}\n")

    result_json = await call_agent(ORCHESTRATOR_URL, vibe)
    program = json.loads(result_json)

    print(json.dumps(program, indent=2))
    print(f"\n🎶  Headline act: {program.get('headline', '?')}")
    print(f"\n📢  {program.get('announcement', '')}")

    prompt = build_poster_prompt(program, config.name)
    print("\n" + "─" * 60)
    print("🎨  Festival poster prompt (paste into any image AI):")
    print("─" * 60)
    print(prompt)
    print("─" * 60 + "\n")


if __name__ == "__main__":
    asyncio.run(main())
