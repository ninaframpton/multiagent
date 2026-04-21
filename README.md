# 🎶 FestBot — A2A Multi-Agent Labcamp

A hands-on labcamp for building a **multi-agent system** using the [A2A protocol](https://github.com/google/a2a) and [Google ADK](https://github.com/google/adk-python).

Agents communicate over HTTP — no shared memory, no direct imports. Just structured messages between independent servers.

---

## 🎯 What you'll build

You'll extend a working pipeline by building a new agent from scratch and wiring it into the system:

```
Orchestrator :8000  (you wire)
      │
  ┌───┼───┐
  ▼   ▼   ▼
Scout Lineup Hype
:8001 :8002 :8003  (you build Hype)
```

Read **[TASK.md](./TASK.md)** for the full step-by-step guide.

---

## 🗂️ Project structure

```
agents/
├── scout/
│   ├── server.py    ✅ provided — ADK LlmAgent + to_a2a()
│   └── handler.py   ✅ provided — scout_artists()
├── lineup/
│   ├── server.py    ✅ provided — ADK LlmAgent + to_a2a()
│   └── handler.py   ✅ provided — build_lineup() with LLM reasoning
├── hype/
│   ├── server.py    ✅ solution — ADK LlmAgent + to_a2a()
│   └── handler.py   ✅ solution — write_announcement()
└── orchestrator/
    ├── server.py    ✅ provided — ADK LlmAgent + to_a2a()
    ├── client.py    ✅ provided — call_agent() helper
    └── handler.py   ✅ solution — run_pipeline()

shared/
└── models.py        ✅ Artist, LineupSlot, FestivalProgram

tools/
├── llm.py           ✅ ask() — wraps Gemini via google-genai
├── lastfm.py        ✅ get_top_artists_by_genre() — real artists, fallback built-in
└── weather.py       ✅ get_forecast() — optional stretch goal

tests/
├── test_hype_handler.py         ✅ tests for Part 1
└── test_orchestrator_handler.py ✅ tests for Part 3
```

---

## 🚀 Quick start

```bash
uv sync
cp .env.example .env   # add GOOGLE_API_KEY, optionally LASTFM_API_KEY

./scripts/start.sh     # start all agents (separate terminal)

uv run python main.py "summer indie road trip"
uv run pytest
```

---

## 🌐 Ports

| Agent | URL |
|---|---|
| Orchestrator | http://localhost:8000 |
| Scout | http://localhost:8001 |
| Lineup | http://localhost:8002 |
| Hype | http://localhost:8003 |

---

## 🧩 The ADK + A2A pattern

Every `server.py` follows this three-line pattern:

```python
agent = LlmAgent(name=..., model="gemini-2.0-flash", tools=[...])
app = to_a2a(agent, host="localhost", port=PORT)
```

`to_a2a()` auto-generates the agent card at `/.well-known/agent-card.json` and
handles all JSON-RPC routing. The Orchestrator discovers agents via their cards
and talks to them through `call_agent()` in `client.py`.

---

## 📚 References

| Resource | Link |
|---|---|
| A2A Protocol | https://github.com/google/a2a |
| Google ADK | https://github.com/google/adk-python |
| ADK docs | https://google.github.io/adk-docs/ |
| Pydantic v2 | https://docs.pydantic.dev |
| Google AI Studio (API key) | https://aistudio.google.com/apikey |
