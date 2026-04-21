"""Last.fm tool — find real artists by genre tag.

No OAuth needed — just an API key.

Setup
-----
1. Create a free Last.fm account at https://www.last.fm/join
2. Register an API application (name it anything) at
   https://www.last.fm/api/account/create
3. Copy the key into .env:

       LASTFM_API_KEY=your_key_here

That's it — no client secret, no redirect URIs, no OAuth flow.

Falls back to a small built-in list if the key is missing, so the
pipeline always works even without credentials configured.
"""

import logging
import os

import httpx
from dotenv import load_dotenv
from pydantic import BaseModel

load_dotenv()

logger = logging.getLogger(__name__)

_BASE_URL = "https://ws.audioscrobbler.com/2.0/"

# Fallback artists used when the API key is not set.
# Keyed by rough genre family so the fallback is at least vaguely relevant.
_FALLBACK: dict[str, list[dict[str, str]]] = {
    "default": [
        {"name": "Arcade Fire",   "genre": "indie rock"},
        {"name": "Bon Iver",      "genre": "indie folk"},
        {"name": "Tame Impala",   "genre": "psychedelic rock"},
        {"name": "LCD Soundsystem","genre": "dance punk"},
        {"name": "Phoebe Bridgers","genre": "indie folk"},
    ],
    "techno": [
        {"name": "Aphex Twin",    "genre": "electronic"},
        {"name": "Bicep",         "genre": "dance"},
        {"name": "Jon Hopkins",   "genre": "ambient techno"},
        {"name": "Four Tet",      "genre": "electronic"},
        {"name": "Floating Points","genre": "electronic"},
    ],
    "jazz": [
        {"name": "Kamasi Washington", "genre": "jazz"},
        {"name": "Nubya Garcia",      "genre": "jazz"},
        {"name": "Makaya McCraven",   "genre": "jazz"},
        {"name": "BadBadNotGood",     "genre": "jazz fusion"},
        {"name": "Sons of Kemet",     "genre": "jazz"},
    ],
    "hip-hop": [
        {"name": "Kendrick Lamar", "genre": "hip-hop"},
        {"name": "Little Simz",    "genre": "hip-hop"},
        {"name": "JPEGMAFIA",      "genre": "experimental hip-hop"},
        {"name": "Injury Reserve", "genre": "alternative hip-hop"},
        {"name": "billy woods",    "genre": "underground hip-hop"},
    ],
}


class LastFmArtist(BaseModel):
    """A real artist returned by the Last.fm tag API."""

    name: str
    genre: str           # the tag used to find them
    lastfm_url: str


async def get_top_artists_by_genre(
    genre: str,
    limit: int = 5,
) -> list[LastFmArtist]:
    """Return the top Last.fm artists for a genre tag.

    Uses the ``tag.getTopArtists`` endpoint — no OAuth required.
    Falls back to a built-in list if the API key is not set.

    Args:
        genre: A genre tag, e.g. ``"indie"``, ``"techno"``, ``"jazz"``.
        limit: Number of artists to return (max 50).

    Returns:
        A list of LastFmArtist entries.
    """
    api_key = os.getenv("LASTFM_API_KEY")
    if not api_key:
        logger.warning(
            "LASTFM_API_KEY not set — using built-in fallback artists."
        )
        return _fallback_artists(genre, limit)

    try:
        return await _fetch(api_key, genre, limit)
    except Exception as exc:  # noqa: BLE001
        logger.warning("Last.fm API call failed (%s) — using fallback.", exc)
        return _fallback_artists(genre, limit)


async def _fetch(
    api_key: str, genre: str, limit: int
) -> list[LastFmArtist]:
    """Call the Last.fm tag.getTopArtists endpoint."""
    params = {
        "method": "tag.gettopartists",
        "tag": genre,
        "api_key": api_key,
        "format": "json",
        "limit": limit,
    }
    async with httpx.AsyncClient(timeout=10) as client:
        response = await client.get(_BASE_URL, params=params)
        response.raise_for_status()
        data = response.json()

    artists = []
    for item in data.get("topartists", {}).get("artist", []):
        artists.append(
            LastFmArtist(
                name=item["name"],
                genre=genre,
                lastfm_url=item.get("url", ""),
            )
        )
    return artists[:limit]


def _fallback_artists(genre: str, limit: int) -> list[LastFmArtist]:
    """Return built-in artists when the API is unavailable."""
    genre_lower = genre.lower()
    bucket = next(
        (key for key in _FALLBACK if key in genre_lower),
        "default",
    )
    return [
        LastFmArtist(name=a["name"], genre=a["genre"], lastfm_url="")
        for a in _FALLBACK[bucket][:limit]
    ]
