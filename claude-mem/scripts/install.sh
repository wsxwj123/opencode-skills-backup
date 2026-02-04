#!/bin/bash
# Installation script for claude-mem skill
# Installs Node.js dependencies using bun

cd "$(dirname "$0")/../repo" || exit 1

echo "Installing claude-mem dependencies..."
bun install

if [ $? -eq 0 ]; then
    echo "✓ Dependencies installed successfully"
else
    echo "✗ Failed to install dependencies"
    exit 1
fi
