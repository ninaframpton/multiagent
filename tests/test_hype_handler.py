"""Tests for the Hype Agent handler.

These tests mock ask() so no API key is needed.
They verify:
  - get_festival_name() returns a non-empty string from config
  - write_announcement() calls ask() with the lineup JSON in the prompt
  - write_announcement() returns the string that ask() produces
"""

from unittest.mock import AsyncMock, patch

import pytest

from agents.hype.handler import get_festival_name, write_announcement
from agents.lineup.handler import LineupResult
from shared.models import LineupSlot

# ── Fixtures ──────────────────────────────────────────────────────────────────

_SLOTS = [
    LineupSlot(
        time="14:00",
        stage="Forest Stage",
        artist="Solar Pines",
        genre="indie folk",
        reason="Gentle opener for the afternoon crowd.",
    ),
    LineupSlot(
        time="22:00",
        stage="Main Stage",
        artist="Crater Club",
        genre="techno",
        reason="High-energy headliner to close the night.",
    ),
]

_LINEUP_JSON = LineupResult(slots=_SLOTS).model_dump_json()
_FAKE_ANNOUNCEMENT = (
    "Welcome to FestBot 2026! Crater Club will close the Main Stage at 22:00 "
    "with relentless techno. This is the night you've been waiting for!"
)


# ── Tests ─────────────────────────────────────────────────────────────────────

def test_get_festival_name_returns_string() -> None:
    """get_festival_name() should return a non-empty string."""
    result = get_festival_name()
    assert isinstance(result, str)
    assert len(result) > 0


@pytest.mark.asyncio
async def test_write_announcement_returns_string() -> None:
    """write_announcement() should return a non-empty string."""
    with patch("agents.hype.handler.ask", AsyncMock(return_value=_FAKE_ANNOUNCEMENT)):
        result = await write_announcement(_LINEUP_JSON)

    assert isinstance(result, str)
    assert len(result) > 0


@pytest.mark.asyncio
async def test_write_announcement_calls_ask_once() -> None:
    """write_announcement() must call ask() exactly once."""
    mock_ask = AsyncMock(return_value=_FAKE_ANNOUNCEMENT)
    with patch("agents.hype.handler.ask", mock_ask):
        await write_announcement(_LINEUP_JSON)

    assert mock_ask.call_count == 1


@pytest.mark.asyncio
async def test_write_announcement_includes_lineup_in_prompt() -> None:
    """The lineup JSON must appear in the ask() prompt."""
    mock_ask = AsyncMock(return_value=_FAKE_ANNOUNCEMENT)
    with patch("agents.hype.handler.ask", mock_ask):
        await write_announcement(_LINEUP_JSON)

    prompt_arg = mock_ask.call_args.args[0]
    assert "Crater Club" in prompt_arg, "Headline artist should appear in the prompt"
