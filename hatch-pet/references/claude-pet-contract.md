# Claude Pet Contract

## Sprite Atlas

- Format: PNG or WebP.
- Dimensions: `1536x1872`.
- Grid: 8 columns x 9 rows.
- Cell: `192x208`.
- Background: transparent.
- Unused cells: fully transparent.

## Local Custom Pet Package

Place files under:

```text
${CLAUDE_HOME:-$HOME/.claude}/pets/<pet-name>/
├── pet.json
└── spritesheet.webp
```

Manifest shape:

```json
{
  "id": "pet-name",
  "displayName": "Pet Name",
  "description": "One short sentence.",
  "spritesheetPath": "spritesheet.webp"
}
```

## Image Generation

**Manual via ChatGPT web (chatgpt.com) — no API required.**

Claude prepares the prompts. The user copies each prompt into GPT Image 2 web and provides the resulting PNG. Claude then runs all deterministic processing.

Required ChatGPT settings per image type:
- Base character: Size 1024×1024, Quality: high
- All 9 row strips: Size 1792×1024, Quality: high
- Attach canonical-base.png as a reference when generating row strips.
