"""A2A client helper for calling downstream agents.

This module is provided for you — no changes needed here.
It handles the boilerplate of connecting to an agent, sending a message,
and collecting the first text artifact from the response stream.
"""

import logging

import httpx
from a2a.client.card_resolver import A2ACardResolver
from a2a.client.client import ClientConfig
from a2a.client.client_factory import ClientFactory
from a2a.types import Message, Part, Role, Task, TaskArtifactUpdateEvent, TextPart
from a2a.utils.parts import get_text_parts

logger = logging.getLogger(__name__)


async def call_agent(base_url: str, text: str) -> str:
    """Send a text message to an A2A agent and return the first text artifact.

    Args:
        base_url: The root URL of the target agent (e.g. "http://localhost:8001").
        text: The text payload to send as a user message.

    Returns:
        The text content of the agent's first artifact.

    Raises:
        RuntimeError: If the agent returns no usable text artifact.
    """
    message = Message(
        role=Role.user,
        parts=[Part(root=TextPart(text=text))],
        message_id="",
    )

    async with httpx.AsyncClient(timeout=120) as http_client:
        resolver = A2ACardResolver(http_client, base_url)
        card = await resolver.get_agent_card()

        config = ClientConfig(httpx_client=http_client, streaming=False)
        factory = ClientFactory(config=config)
        client = factory.create(card)

        async for event in client.send_message(message):
            # Non-streaming: SDK yields (Task, None) — artifact is on the Task.
            # Streaming: SDK yields (Task, TaskArtifactUpdateEvent).
            task_obj = event[0] if isinstance(event, tuple) else None
            update = event[1] if isinstance(event, tuple) else event

            # Prefer the update artifact (streaming path)
            if isinstance(update, TaskArtifactUpdateEvent):
                texts = get_text_parts(update.artifact.parts or [])
                if texts:
                    return texts[0]

            # Fall back to Task.artifacts (non-streaming path)
            if isinstance(task_obj, Task) and task_obj.artifacts:
                for artifact in task_obj.artifacts:
                    texts = get_text_parts(artifact.parts or [])
                    if texts:
                        return texts[0]

    raise RuntimeError(f"No text artifact received from agent at {base_url}")
