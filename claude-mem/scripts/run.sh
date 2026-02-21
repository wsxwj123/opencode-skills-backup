#!/bin/bash
# claude-mem MCP launcher for OpenCode
# Ensures worker is running, then starts MCP server (stdio)

REPO_DIR="$HOME/.config/opencode/skills/claude-mem/repo"
PLUGIN_DIR="$REPO_DIR/plugin"
SCRIPTS_DIR="$PLUGIN_DIR/scripts"
WORKER_URL="http://127.0.0.1:37777"

# Check if worker is alive
if ! curl -s --max-time 2 "$WORKER_URL/health" >/dev/null 2>&1; then
  # Start worker in background
  cd "$PLUGIN_DIR" && bun "$SCRIPTS_DIR/worker-service.cjs" start >/dev/null 2>&1 &
  # Wait for worker to be ready (max 10s)
  for i in $(seq 1 20); do
    if curl -s --max-time 1 "$WORKER_URL/health" >/dev/null 2>&1; then
      break
    fi
    sleep 0.5
  done
fi

# Launch MCP server (stdio mode for OpenCode)
exec bun "$SCRIPTS_DIR/mcp-server.cjs"
