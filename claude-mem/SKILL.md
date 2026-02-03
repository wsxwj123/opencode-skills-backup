name: claude-mem
description: Persistent memory system for maintaining context across sessions. Provides search, timeline, and observation retrieval tools.
github_url: https://github.com/thedotmack/claude-mem
github_hash: 1341e93fcab15b9caf48bc947d8521b4a97515d8
version: 9.0.12
created_at: 2026-02-03T00:00:00Z
entry_point: scripts/run.sh
dependencies: ["bun", "node"]
tools:
  - name: search
    description: Search memory index with full-text queries, filters by type/date/project. Returns index with IDs.
  - name: timeline
    description: Get chronological context around a specific observation ID or query.
  - name: get_observations
    description: Fetch full details for specific observation IDs.
  - name: __IMPORTANT
    description: Documentation for the memory search workflow.
