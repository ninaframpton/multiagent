"""Tests for the Orchestrator handler.

These tests mock call_agent() so no running agents or API keys are needed.
They verify that run_pipeline() correctly sequences Scout → Lineup → Hype
and assembles a valid FestivalProgram.
"""

from unittest.mock import AsyncMock, patch

from agents.lineup.handler import LineupResult
from agents.orchestrator.handler import run_pipeline
from shared.models import Artist, ArtistList, FestivalProgram, LineupSlot

# ── Fixtures ──────────────────────────────────────────────────────────────────

_ARTISTS = [
    Artist(name="Crater Club", genre="techno", description="Pounding basslines"),
    Artist(name="Solar Pines", genre="indie folk", description="Dreamy harmonies"),
]

_SLOTS = [
    LineupSlot(
        time="14:00",
        stage="Forest Stage",
        artist="Solar Pines",
        genre="indie folk",
        reason="Gentle afternoon opener.",
    ),
    LineupSlot(
        time="22:00",
        stage="Main Stage",
        artist="Crater Club",
        genre="techno",
        reason="High-energy headliner to close the night.",
    ),
]

_ARTIST_JSON = ArtistList(artists=_ARTISTS).model_dump_json()
_LINEUP_JSON = LineupResult(slots=_SLOTS).model_dump_json()
_ANNOUNCEMENT = "Welcome to FestBot 2026! Crater Club closes the night!"


def _make_mock() -> AsyncMock:
    """Return a call_agent mock that sequences Scout → Lineup → Hype responses."""
    mock = AsyncMock()
    mock.side_effect = [_ARTIST_JSON, _LINEUP_JSON, _ANNOUNCEMENT]
    return mock


# ── Tests ─────────────────────────────────────────────────────────────────────

async def test_run_pipeline_returns_festival_program() -> None:
    """run_pipeline() should return a FestivalProgram."""
    with patch("agents.orchestrator.handler.call_agent", _make_mock()):
        result = await run_pipeline("dark techno underground")

    assert isinstance(result, FestivalProgram)


async def test_run_pipeline_calls_all_three_agents() -> None:
    """run_pipeline() must call Scout, Lineup, and Hype — in that order."""
    mock = _make_mock()
    with patch("agents.orchestrator.handler.call_agent", mock):
        await run_pipeline("dark techno underground")

    assert mock.call_count == 3  # noqa: PLR2004
    urls = [call.args[0] for call in mock.call_args_list]
    assert "8001" in urls[0], "First call should go to Scout (:8001)"
    assert "8002" in urls[1], "Second call should go to Lineup (:8002)"
    assert "8003" in urls[2], "Third call should go to Hype (:8003)"


async def test_run_pipeline_chains_outputs_as_inputs() -> None:
    """Each agent's output must be passed as the next agent's input."""
    mock = _make_mock()
    with patch("agents.orchestrator.handler.call_agent", mock):
        await run_pipeline("dark techno underground")

    calls = mock.call_args_list
    assert calls[1].args[1] == _ARTIST_JSON, "Lineup should receive Scout's output"
    assert calls[2].args[1] == _LINEUP_JSON, "Hype should receive Lineup's output"


async def test_run_pipeline_headline_is_last_slot_by_time() -> None:
    """The headline should be the artist in the latest time slot."""
    with patch("agents.orchestrator.handler.call_agent", _make_mock()):
        result = await run_pipeline("dark techno underground")

    assert result.headline == "Crater Club"


async def test_run_pipeline_announcement_comes_from_hype() -> None:
    """The announcement in FestivalProgram should be what Hype returned."""
    with patch("agents.orchestrator.handler.call_agent", _make_mock()):
        result = await run_pipeline("dark techno underground")

    assert result.announcement == _ANNOUNCEMENT


async def test_run_pipeline_slots_match_lineup() -> None:
    """The FestivalProgram slots should match what Lineup returned."""
    with patch("agents.orchestrator.handler.call_agent", _make_mock()):
        result = await run_pipeline("dark techno underground")

    assert len(result.slots) == len(_SLOTS)
    assert {s.artist for s in result.slots} == {s.artist for s in _SLOTS}
