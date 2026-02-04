#!/bin/bash
# Claude-Mem MCP Server Launcher
# This script ensures the worker service is running and launches the MCP server

SKILL_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
REPO_DIR="$SKILL_DIR/repo"

cd "$REPO_DIR" || exit 1

# Start worker service (suppresses output to not interfere with MCP JSON-RPC)
bun plugin/scripts/worker-service.cjs start >/dev/null 2>&1

# Give worker a moment to initialize
sleep 1

# Run MCP server (uses stdio for JSON-RPC communication)
exec node plugin/scripts/mcp-server.cjs
