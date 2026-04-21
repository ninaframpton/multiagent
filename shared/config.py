"""Load festival configuration from config.yaml."""

from functools import lru_cache
from pathlib import Path

import yaml
from pydantic import BaseModel

_CONFIG_PATH = Path(__file__).parent.parent / "config.yaml"


class FestivalConfig(BaseModel):
    """Typed representation of the festival section in config.yaml."""

    name: str
    vibe: str
    genre: str
    location: str
    date: str
    stages: list[str]


@lru_cache(maxsize=1)
def get_config() -> FestivalConfig:
    """Return the festival config, cached after the first read.

    Returns:
        A FestivalConfig loaded from config.yaml.
    """
    raw = yaml.safe_load(_CONFIG_PATH.read_text())
    return FestivalConfig(**raw["festival"])
