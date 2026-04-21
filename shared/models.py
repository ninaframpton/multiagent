"""Shared Pydantic models used across all agents."""

from pydantic import BaseModel


class Artist(BaseModel):
    """A festival artist returned by the Scout Agent."""

    name: str
    genre: str
    description: str


class ArtistList(BaseModel):
    """A list of scouted artists."""

    artists: list[Artist]


class LineupSlot(BaseModel):
    """A single slot in the festival lineup, produced by the Lineup Agent."""

    time: str    # e.g. "21:00"
    stage: str
    artist: str
    genre: str
    reason: str  # Why the Lineup Agent placed this artist here


class FestivalProgram(BaseModel):
    """The final output produced by the Orchestrator."""

    vibe: str
    headline: str
    slots: list[LineupSlot]
    announcement: str  # Crowd-hype announcement written by the Hype Agent
