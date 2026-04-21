# 🎪 FestBot — Build and Wire a New Agent

You're going to extend a working multi-agent system by building a brand new agent from scratch and plugging it into an existing pipeline.

**You implement three things, in order.** Everything else is already provided.

---

## The System

Four agents communicate over the A2A protocol. Three are already built and running:

```
  Orchestrator :8000   ← Part 3: you wire this
          │  A2A messages (JSON-RPC over HTTP)
    ┌─────┼──────────┐
    ▼     ▼          ▼
 Scout  Lineup     Hype
 :8001  :8002     :8003  ← Parts 1 & 2: you build this
```

| Agent | What it does | Input | Output |
|---|---|---|---|
| **Scout** `:8001` | Fetches real artists from Last.fm, then asks Gemini to describe each one | vibe string | ArtistList JSON |
| **Lineup** `:8002` | Uses tools to score each artist's energy, then builds a reasoned schedule | ArtistList JSON | LineupResult JSON |
| **Hype** `:8003` | *You build this* — writes a crowd announcement using two tools | LineupResult JSON | announcement string |
| **Orchestrator** `:8000` | *You wire this* — calls Scout → Lineup → Hype in sequence | vibe string | FestivalProgram JSON |

The key idea: each agent is a **separate HTTP server**. They don't import each other's code. The Orchestrator connects them purely by passing messages — one agent's JSON output becomes the next agent's text input.

---

## Step 0 — Setup (2 min)

```bash
uv sync
cp .env.example .env
```

Add your Google API key to `.env` (get one free at https://aistudio.google.com/apikey):

```
GOOGLE_API_KEY=AIza...
```

Optionally add a Last.fm key to get real artist names from the API. Without
it, Scout falls back to a built-in list — the pipeline works either way:

```
LASTFM_API_KEY=your_key_here   # https://www.last.fm/api/account/create
```

---

## Step 1 — Read the Lineup agent (5 min)

Before writing any code, read [agents/lineup/server.py](agents/lineup/server.py).

The Lineup agent is a good example of how [**ADK `FunctionTool`s**](https://google.github.io/adk-docs/tools-custom/function-tools/) work. The [`LlmAgent`](https://google.github.io/adk-docs/agents/llm-agents/) has three tools it can call itself:

- `get_stages()` — reads stage names from `config.yaml`
- `get_artist_energy(name, genre)` — calls Gemini to rate one artist's crowd energy 1–10
- `build_lineup_tool(artist_list_json)` — builds the final schedule

The agent decides *when* to call each tool, what arguments to pass, and uses the results to reason about placement.

This is the pattern you'll follow for the Hype agent — except your agent will have two tools instead of three.

---

## Part 1 — Implement the Hype handler (8 min)

**File:** `agents/hype/handler.py`

`get_festival_name()` is already implemented. You just need to implement
`write_announcement()`.

Call `ask()` (already imported) with a prompt that includes the lineup JSON
and a system instruction telling Gemini it's a festival MC. Return the reply
as a plain string.

Run the tests to check — no API key needed, `ask()` is mocked:

```bash
uv run pytest tests/test_hype_handler.py -v
```

---

## Part 2 — Build the Hype server (12 min)

**File:** `agents/hype/server.py`

Your Hype agent needs **two `FunctionTool`s** — one for each function in `handler.py`.
The agent should call `get_festival_name_tool` first to find the festival name,
then call `write_announcement_tool` with the lineup JSON.

Follow the three-step pattern from [agents/lineup/server.py](agents/lineup/server.py):

1. Write a tool function wrapping each handler function
2. Create an `LlmAgent` with both tools and an `instruction` telling it to call `get_festival_name_tool` first, then `write_announcement_tool`
3. Call `to_a2a(agent, host="localhost", port=PORT)` to produce `app`, and delete the `NotImplementedError`

Verify your agent card appears:

```bash
uv run uvicorn agents.hype.server:app --port 8003 &
curl http://localhost:8003/.well-known/agent-card.json | python3 -m json.tool
```

---

## Part 3 — Wire the Orchestrator (10 min)

**File:** `agents/orchestrator/handler.py`

Implement `run_pipeline()`. Call each agent in sequence using `call_agent()`,
then assemble the `FestivalProgram`. All imports are already at the top of the file.

```python
async def run_pipeline(vibe: str) -> FestivalProgram:
    # 1. Scout — send the vibe, get back artist JSON
    artist_json = await call_agent(SCOUT_URL, vibe)

    # 2. Lineup — send artist JSON, get back lineup JSON
    lineup_json = await call_agent(LINEUP_URL, artist_json)

    # 3. Hype — send lineup JSON, get back an announcement string
    announcement = await call_agent(HYPE_URL, lineup_json)

    # 4. Parse the lineup and assemble the program
    lineup = LineupResult.model_validate_json(lineup_json)
    headline = lineup.slots[-1].artist  # last slot by time = headliner

    return FestivalProgram(
        vibe=vibe,
        headline=headline,
        slots=lineup.slots,
        announcement=announcement,
    )
```

Run all tests:

```bash
uv run pytest -v
```

---

## Step 4 — Run the full pipeline (2 min)

```bash
./scripts/start.sh   # starts all 4 agents

# In a second terminal:
uv run python main.py "dark techno underground"
```

You'll see the full `FestivalProgram` JSON, the headline act, the crowd
announcement your Hype agent wrote, and an image prompt to paste into an AI
image generator.

---

## ✅ Done? Check these

- [ ] `uv run pytest` passes (10 tests, no API calls needed)
- [ ] `curl http://localhost:8003/.well-known/agent-card.json` returns your Hype agent's card — with both tools listed
- [ ] `uv run python main.py` prints a complete program with an announcement
- [ ] The `reason` field on each slot explains why that artist is on that stage
- [ ] Changing `config.yaml` → `vibe` changes the artists and lineup

---

## 💡 Stretch goals

- **ADK Parallel workflow** ([docs](https://google.github.io/adk-docs/agents/workflow-agents/parallel-agents/)): in `agents/orchestrator/server.py`, replace the single Scout step with a `ParallelAgent` that runs two Scout sub-steps (for example, one with the user vibe and one with a slightly broader variant), then merge/deduplicate artists before sending to Lineup
- **Add a fourth agent**: create a `Poster` agent that takes the `FestivalProgram` and returns formatted text suitable for social media

---

## 🔬 Going deeper with ADK

### ADK callbacks — watch the Lineup agent think

ADK lets you hook into an agent's tool calls with `after_tool_callback`
([docs](https://google.github.io/adk-docs/callbacks/types-of-callbacks/)).
Add one to the Lineup agent so you can watch it score each artist in real time.

In `agents/lineup/server.py`, define a callback and pass it to the `LlmAgent`:

```python
from google.adk.agents.llm_agent import AfterToolCallback
from google.adk.tools.base_tool import BaseTool
from google.adk.agents.context import Context

def log_energy_score(
    tool: BaseTool,
    args: dict,
    tool_context: Context,
    tool_response: dict,
) -> None:
    if tool.name == "get_artist_energy":
        print(f"  energy score → {args['name']}: {tool_response['result']}/10")

agent = LlmAgent(
    ...
    after_tool_callback=log_energy_score,
)
```

Restart the Lineup agent and run the pipeline — you'll see each score printed as
the agent calls `get_artist_energy` for each artist before building the schedule.

---

### ADK Runner — call an agent without an HTTP server

The A2A protocol is great for inter-agent communication, but ADK also has a
lower-level `Runner` API ([docs](https://adk.dev/runtime/event-loop/)) for
calling an agent directly in-process — no HTTP, no uvicorn. This is how `to_a2a()` works internally.

Create a small script `scripts/run_scout.py` and try it:

```python
import asyncio
from google.adk.runners import Runner
from google.adk.sessions import InMemorySessionService
from google.genai import types
from agents.scout.server import agent  # the LlmAgent you already have

async def main() -> None:
    session_service = InMemorySessionService()
    session = await session_service.create_session(
        app_name="festbot", user_id="dev"
    )
    runner = Runner(
        app_name="festbot",
        agent=agent,
        session_service=session_service,
    )
    async for event in runner.run_async(
        user_id="dev",
        session_id=session.id,
        new_message=types.Content(
            role="user",
            parts=[types.Part(text="summer indie road trip")],
        ),
    ):
        if event.is_final_response():
            print(event.content.parts[0].text)

asyncio.run(main())
```

Run it with `uv run python scripts/run_scout.py`. Compare what you get back to
what `call_agent("http://localhost:8001", "summer indie road trip")` returns —
they're the same agent, just reached two different ways.

---

## 📚 References

| Resource | Link |
|---|---|
| A2A Protocol | https://github.com/google/a2a |
| Google ADK | https://github.com/google/adk-python |
| ADK docs | https://google.github.io/adk-docs/ |
| Pydantic v2 | https://docs.pydantic.dev |
| Google AI Studio (API key) | https://aistudio.google.com/apikey |
