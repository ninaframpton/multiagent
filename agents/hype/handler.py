"""Hype Agent handler — write a crowd announcement for the festival lineup.

🔧 TODO: This is the first file you implement (Part 1 of 3).

Your job: implement write_announcement() by calling ask() with a prompt that
includes the lineup JSON and instructs Gemini to write an exciting 2–3 sentence
crowd announcement mentioning the headline act.

The LlmAgent in server.py calls get_festival_name() as a tool *before* calling
write_announcement(), so Gemini already has the festival name in context when
it calls this tool — you don't need to look it up here.
"""

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
        "Tonight's headline act Crater Club will close out the Main Stage
        at 22:00 with their trademark pounding techno.
        Get ready for the night of your life!"

    Note:
        The LlmAgent in server.py calls get_festival_name_tool() *before*
        calling this tool, so Gemini already has the festival name in context.
        You don't need to pass it as a parameter here.
    """
    raise NotImplementedError("Implement write_announcement() — see TASK.md")
