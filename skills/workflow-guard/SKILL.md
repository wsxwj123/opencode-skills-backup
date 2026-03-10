---
name: workflow-guard
description: Use when you want Claude Code to enforce a mandatory edit workflow using PreToolUse hooks, activation markers, and stale-session blocking.
---

# Workflow Guard Skill

This skill turns workflow rules into hard gates for Claude Code file edits.

Core model:
- Skill = SOP definition.
- Hook = enforcement.
- Marker file (`.workflow-active`) = session state.

## Included Files

```text
workflow-guard-skill/
  SKILL.md
  scripts/
    workflow_common.py
    workflow_activate.py
    workflow_session_check.py
    workflow_gate.py
```

## Behavior

`workflow_gate.py` guards `Edit|Write|MultiEdit|NotebookEdit` when:
- project is workflow-managed (`PROJECT.md` exists), and
- marker state is checked before edit.

Default mode is auto-activation:
- missing/stale/invalid `.workflow-active` is created/refreshed automatically.
- strict blocking can be restored with `--no-auto-activate`.

Default TTL is 4 hours.

Bootstrap exemptions are built in for:
- `.claude/hooks/workflow-gate.py`
- `.claude/hooks/workflow-session-check.py`
- `.claude/hooks/workflow-activate.py`

## Install

1. Copy this folder to:
`~/.claude/skills/workflow-guard/`

2. Add project marker in each managed repo:
`PROJECT.md`

3. Register hook in `~/.claude/settings.json` or `.claude/settings.json`:

```json
{
  "hooks": {
    "PreToolUse": [
      {
        "matcher": "Edit|Write|MultiEdit|NotebookEdit",
        "hooks": [
          {
            "type": "command",
            "command": "python3 \"$HOME/.claude/skills/workflow-guard/scripts/workflow-gate.py\" --auto-activate --ttl-hours 4"
          }
        ]
      }
    ]
  }
}
```

You can also add a second check hook if needed:

```json
{
  "type": "command",
  "command": "python3 \"$HOME/.claude/skills/workflow-guard/scripts/workflow-session-check.py\""
}
```

## Daily Use

In auto-activation mode, no manual command is required.

Optional manual activation is still available:

```bash
python3 "$HOME/.claude/skills/workflow-guard/scripts/workflow-activate.py" --project-root "$PWD" --ttl-hours 4
```

If you prefer strict mode, set hook command to:

```bash
python3 "$HOME/.claude/skills/workflow-guard/scripts/workflow-gate.py" --no-auto-activate
```

## Quick Validation

1. Ensure repo contains `PROJECT.md`.
2. Ask Claude to edit a file.
3. Confirm `.workflow-active` is auto-created.
4. For strict mode testing, use `--no-auto-activate` and verify block behavior.

## Notes

- Blocking uses `exit 2` and stderr feedback.
- Hook input is read from stdin JSON (`tool_name`, `tool_input`, `cwd`).
- Scripts force UTF-8 stdout/stderr for cross-platform stability.
