#!/usr/bin/env bash
# scripts/start.sh — Start all FestBot agents in the background.
# Usage: ./scripts/start.sh

set -euo pipefail

ROOT="$(cd "$(dirname "$0")/.." && pwd)"
PIDS=()
PORTS=(8000 8001 8002 8003)

cleanup() {
    for pid in "${PIDS[@]:-}"; do
        if kill -0 "$pid" 2>/dev/null; then
            kill "$pid" 2>/dev/null || true
        fi
    done
}

check_port_free() {
    local port="$1"
    if ss -ltn "sport = :${port}" | awk 'NR>1 {found=1} END {exit !found}'; then
        echo "❌  Port ${port} is already in use."
        echo "    Stop existing processes first (if available): kill \$(lsof -ti:${port})"
        exit 1
    fi
}

wait_for_agent_card() {
    local name="$1"
    local port="$2"
    local url="http://localhost:${port}/.well-known/agent-card.json"

    for _ in {1..20}; do
        if curl -fsS "$url" >/dev/null 2>&1; then
            return 0
        fi
        sleep 0.5
    done

    echo "❌  ${name} did not become ready on port ${port}."
    return 1
}

trap cleanup EXIT

start_agent() {
    local name="$1"
    local module="$2"
    local port="$3"

    echo "▶  Starting ${name} on port ${port}..."
    (
        cd "$ROOT"
        uv run uvicorn "${module}:app" --host 0.0.0.0 --port "${port}"
    ) &
    local pid=$!
    PIDS+=("$pid")
    echo "   PID ${pid}"
}

for port in "${PORTS[@]}"; do
    check_port_free "$port"
done

start_agent "Scout Agent"   "agents.scout.server"        8001
start_agent "Lineup Agent"  "agents.lineup.server"       8002
start_agent "Hype Agent"    "agents.hype.server"         8003
start_agent "Orchestrator"  "agents.orchestrator.server" 8000

echo ""
echo "⏳  Waiting for agents to boot..."

wait_for_agent_card "Scout Agent"  8001
wait_for_agent_card "Lineup Agent" 8002
wait_for_agent_card "Hype Agent"   8003
wait_for_agent_card "Orchestrator" 8000

echo ""
echo "✅  All agents running. Agent cards available at:"
echo "    http://localhost:8000/.well-known/agent-card.json  (Orchestrator)"
echo "    http://localhost:8001/.well-known/agent-card.json  (Scout)"
echo "    http://localhost:8002/.well-known/agent-card.json  (Lineup)"
echo "    http://localhost:8003/.well-known/agent-card.json  (Hype)"
echo ""
echo "Run the demo:       uv run python main.py \"summer indie road trip\""
echo "Stop all agents:    kill \$(lsof -ti:8000,8001,8002,8003)"

trap - EXIT

wait
