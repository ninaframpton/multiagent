# CLAUDE.md — Coding Standards & Project Guidelines

This file defines the conventions for this project. Follow them consistently across every file you create or modify.

---

## Project Overview

FestBot is a Python multi-agent system built on the [A2A protocol](https://github.com/google/a2a) and [Google ADK](https://github.com/google/adk-python). Each agent is an `LlmAgent` exposed via `to_a2a()`. The project uses `uv` for package management and targets Python ≥ 3.12.

**The only files participants need to touch are the `handler.py` files.** Everything else is scaffolded.

---

## Code Style

- **Follow PEP 8** strictly: 4-space indentation, 79-char line limit, two blank lines between top-level definitions.
- **Type annotations are mandatory** on every function signature and class attribute.
- **Docstrings** (Google style) on every public function, class, and module. One-liners are fine for obvious helpers.
- Prefer **`f-strings`** over `.format()` or `%` formatting.
- No bare `except:` — always catch a specific exception type.

```python
# ✅ Good
async def scout_artists(vibe: str) -> ArtistList:
    """Return 5 artists suited to the given festival vibe."""
    ...

# ❌ Bad
async def scout(v):
    ...
```

---

## Project Structure

```
agents/<name>/
    server.py     # LlmAgent + to_a2a() setup — do not edit
    handler.py    # Business logic — this is what you implement
shared/
    models.py     # Pydantic models — do not edit
tests/
    test_<name>_handler.py
```

- **`server.py` wires HTTP; `handler.py` contains logic.** Never mix them.
- **Never import between agent packages.** All cross-agent communication goes via `call_agent()` in `agents/orchestrator/client.py`.

---

## Key SDK Patterns

### Server (already wired in each `server.py`)

```python
from google.adk.agents import LlmAgent
from google.adk.a2a.utils.agent_to_a2a import to_a2a
from google.adk.tools import FunctionTool

async def my_tool(input: str) -> str:
    """Tool docstring — ADK uses this as the tool description."""
    result = await my_handler(input)
    return result.model_dump_json()

agent = LlmAgent(
    name="my_agent",
    model="gemini-2.0-flash",
    description="One-line agent description.",
    instruction="Tell the agent what to do and how to use its tools.",
    tools=[FunctionTool(func=my_tool)],
)

app = to_a2a(agent, host="localhost", port=PORT)
```

`to_a2a()` auto-generates the agent card at `/.well-known/agent-card.json` and handles all JSON-RPC routing.

### Client (already implemented in `agents/orchestrator/client.py`)

```python
from agents.orchestrator.client import call_agent

# Send text to an agent, get back a text artifact
result_json = await call_agent("http://localhost:8001", vibe)
```

### Pydantic models (in `shared/models.py`)

```
Artist          — name: str, genre: str, description: str
ArtistList      — artists: list[Artist]
LineupSlot      — time: str, stage: str, artist: str, genre: str, reason: str
FestivalProgram — vibe: str, headline: str, slots: list[LineupSlot], announcement: str
```

### Handler-local models (defined in each `handler.py`)

```
ArtistList      — agents/scout/handler.py   (also in shared/models.py)
LineupResult    — agents/lineup/handler.py
```

---

## Dependencies

- Use **`uv`** to add packages: `uv add <package>`
- **`google-adk`** — LlmAgent, FunctionTool, to_a2a(), and orchestration primitives
- **`a2a-sdk[http-server]`** — A2A protocol transport layer (used by ADK internally)
- **Pydantic v2** — all data models use `.model_validate_json()` / `.model_dump_json()`
- **`httpx`** (async) — used internally by `call_agent()`
- **`uvicorn`** — ASGI server for each agent

---

## Async

- All handler functions must be **`async def`**.
- Use `asyncio` — not threads.

---

## Error Handling

- Never let an unhandled exception escape a handler — `to_a2a()` in `server.py` will propagate it as an A2A error.
- Log with `logging`, not `print`. Configure logging at the entry point only.

```python
import logging
logger = logging.getLogger(__name__)
```

---

## Testing

- Tests live in `tests/test_<agent>_handler.py` and are pre-written.
- Run with: `uv run pytest`
- Tests use `pytest-asyncio` with `asyncio_mode = "auto"` (set in `pyproject.toml`).
- Test pure logic only — no running servers needed.

---

## Running the Project

```bash
./scripts/start.sh              # start all 4 agents
uv run python main.py "vibe"    # end-to-end demo
uv run pytest                   # run tests
```

Agent card endpoint for any agent: `GET /.well-known/agent-card.json`

---

## What to Avoid

- ❌ `import *`
- ❌ Importing from another agent's package directly — use `call_agent()` instead
- ❌ Editing `server.py`, `client.py`, `shared/models.py`, or `main.py` (unless doing a stretch goal)
- ❌ Magic numbers — use named constants
- ❌ `print()` for logging — use `logging.getLogger(__name__)`

