#!/bin/bash
SKILL_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
REPO_DIR="$SKILL_DIR/repo"

cd "$REPO_DIR"

# Ensure worker service is running
# We suppress output because we need stdout for the MCP server JSON-RPC
bun plugin/scripts/worker-service.cjs start >/dev/null 2>&1

# Run MCP server
# It uses stdio for communication
node plugin/scripts/mcp-server.cjs
