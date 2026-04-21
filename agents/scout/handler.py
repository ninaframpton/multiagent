"""Scout Agent handler — find real artists for the given festival vibe.

This handler is provided for you — no changes needed.

It works in two steps:
  1. Calls Last.fm to fetch real artists by genre (falls back to a built-in
     list if LASTFM_API_KEY is not set — so it always works).
  2. Passes those real artist names to Gemini, which writes a one-line
     festival description for each one.
"""

import json

from shared.models import Artist, ArtistList
from tools.lastfm import get_top_artists_by_genre
from tools.llm import ask


async def scout_artists(vibe: str, genre: str = "indie") -> ArtistList:
    """Return 5 real artists suited to the given festival vibe.

    Fetches real artist names from Last.fm, then uses Gemini to write a
    short festival-appropriate description for each one.

    Args:
        vibe: A natural-language festival vibe string.
        genre: A genre tag passed to Last.fm (e.g. "indie", "techno", "jazz").

    Returns:
        An ArtistList containing 5 Artist entries with real names.
    """
    lastfm_artists = await get_top_artists_by_genre(genre, limit=5)

    names_text = "\n".join(f"- {a.name}" for a in lastfm_artists)
    reply = await ask(
        f"These artists are playing a {vibe!r} festival:\n{names_text}\n\n"
        "For each artist write a single evocative sentence describing their "
        "sound and why they fit this festival. "
        "Reply ONLY with a JSON array of objects with 'name' and 'description' "
        "fields — no markdown, no explanation:\n"
        '[{"name":"...","description":"..."},...]',
        system=(
            "You are a music curator writing festival programme notes. "
            "Reply with raw JSON only. No markdown code fences, no extra text."
        ),
    )
    clean = reply.strip().removeprefix("```json").removeprefix("```").removesuffix("```").strip()
    data = json.loads(clean)
    genre_by_name = {a.name: a.genre for a in lastfm_artists}
    return ArtistList(
        artists=[
            Artist(
                name=item["name"],
                genre=genre_by_name.get(item["name"], genre),
                description=item["description"],
            )
            for item in data
        ]
    )
