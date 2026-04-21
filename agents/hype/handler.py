"""Hype Agent handler — write a crowd announcement for the festival lineup."""

from shared.config import get_config
from tools.llm import ask


def get_festival_name() -> str:
    """Return the festival name from config.yaml.

    The LlmAgent will call this tool automatically to find out the festival
    name before writing the announcement.

    Returns:
        The festival name string, e.g. "FestBot 2026".
    """
    return get_config().name


async def write_announcement(lineup_json: str) -> str:
    """Write a short crowd-hype announcement for the festival lineup.

    Args:
        lineup_json: A JSON string containing the festival lineup. It has a
            "slots" array where each slot has time, stage, artist, genre, and
            reason fields. The last slot by time is the headline act.

    Returns:
        A 2–3 sentence announcement string to be read out to the crowd.

    Example return value:
        "Welcome to FestBot 2026! Tonight's headline act Crater Club will
        close out the Main Stage at 22:00 with their trademark pounding
        techno. Get ready for the night of your life!"
    """
    festival_name = get_festival_name()
    reply = await ask(
        f"Festival name: {festival_name}\n\n"
        f"Here is the festival lineup JSON:\n{lineup_json}\n\n"
        "Write a 2-3 sentence crowd announcement. Mention the headline act "
        "and build excitement for the audience.",
        system="You are an enthusiastic festival MC.",
    )
    return reply
