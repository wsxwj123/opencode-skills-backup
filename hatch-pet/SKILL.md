---
name: hatch-pet
description: Create, repair, validate, visually QA, and package animated Claude pets. The user provides images generated manually via GPT Image 2 web (chatgpt.com). Claude handles everything else: preparing prompts, processing images, assembling the spritesheet, running QA, and packaging the final pet.json + spritesheet.webp into ~/.claude/pets/. Use when the user wants to create a Claude pet from a concept, brand, or visual reference.
---

# Hatch Pet (Claude Edition)

## Overview

Produce a Claude-compatible animated pet spritesheet and pet.json. The user generates each image manually via the GPT Image 2 web interface (chatgpt.com) using the prompts Claude prepares. Claude handles all deterministic work: folder preparation, prompt generation, image processing, atlas assembly, QA, and packaging.

**Image generation is manual**: Claude never calls any image API. Instead, Claude outputs each prompt clearly, the user copies it into ChatGPT web, and then provides the generated image file to Claude.

## Visible Progress Plan

Keep this checklist visible for every pet run. Update it as each step completes.

1. Getting `<Pet>` ready.
2. Imagining `<Pet>`'s main look. *(user generates base image)*
3. Picturing `<Pet>`'s poses. *(user generates 9 animation rows)*
4. Hatching `<Pet>`. *(Claude processes, validates, and packages)*

Only mark a step done when the real file or decision exists.

## Generation Prompt Format

When presenting a prompt for the user to paste into ChatGPT:

1. Show the image type (Base Character / Row: idle / Row: running-right / etc.)
2. Show the frame count and size expected
3. Show the full prompt text in a code block
4. List the GPT Image 2 settings to use
5. Tell the user what to name/save the file as and where to put it

After showing a prompt, wait for the user to confirm they have the image before moving on.

## Default Workflow

### Step 1 — Prepare the run

```bash
SKILL_DIR="${CLAUDE_HOME:-$HOME/.claude}/skills/hatch-pet"
python "$SKILL_DIR/scripts/prepare_pet_run.py" \
  --pet-name "<Name>" \
  --description "<one sentence>" \
  --output-dir /absolute/path/to/run \
  --pet-notes "<stable pet description>" \
  --style-preset auto \
  --force
```

Optional flags:
- `--reference /path/to/ref.png` — user-supplied reference art
- `--style-notes "<freeform>"` — extra style guidance

This creates:
```
run/
  pet_request.json
  imagegen-jobs.json
  prompts/base-pet.md
  prompts/rows/<state>.md       (9 files)
  prompts/row-retries/<state>.md
  references/layout-guides/<state>.png
```

### Step 2 — Base character

Read `prompts/base-pet.md`. Present it to the user:

```
─────────────────────────────────────────────
BASE CHARACTER — paste this into ChatGPT (GPT Image 2):
─────────────────────────────────────────────
<full prompt text>
─────────────────────────────────────────────
Settings: Size 1024×1024, Quality: high
Save as: <run-dir>/decoded/base.png
─────────────────────────────────────────────
```

Wait for the user to provide the file. Once received:
- Copy it to `decoded/base.png`
- Copy it to `references/canonical-base.png` (this becomes the identity lock for all rows)
- Mark the `base` job complete in `imagegen-jobs.json`

### Step 3 — Animation rows

Generate rows in this order:
1. idle
2. running-right
3. running-left *(may be mirrored from running-right — check first)*
4. waving
5. jumping
6. failed
7. waiting
8. running
9. review

For each row, read `prompts/rows/<state>.md` and present it to the user:

```
─────────────────────────────────────────────
ROW: <state> (<N> frames) — paste this into ChatGPT:
─────────────────────────────────────────────
<full prompt text>
─────────────────────────────────────────────
Settings: Size 1792×1024 (wide), Quality: high
IMPORTANT: Also attach your canonical-base.png as a reference image.
Save as: <run-dir>/decoded/<state>.png
─────────────────────────────────────────────
```

Wait for the user to provide the file. Copy to `decoded/<state>.png` and mark the job complete.

**running-left mirror check**: After receiving `running-right`, show the image to the user and ask:
> "Does this pet look safe to mirror for running-left? Check that no asymmetric markings, props, or text would look wrong when flipped."
Only mirror if the user confirms. Otherwise generate normally.

### Step 4 — Mirror running-left (if approved)

```bash
python "$SKILL_DIR/scripts/derive_running_left_from_running_right.py" \
  --run-dir /absolute/path/to/run \
  --confirm-appropriate-mirror \
  --decision-note "<user confirmation note>"
```

This mirrors each frame individually, preserving frame order and timing.

### Step 5 — Process, validate, and QA

Run all deterministic scripts after every row is received and placed:

```bash
RUN_DIR=/absolute/path/to/run
SKILL_DIR="${CLAUDE_HOME:-$HOME/.claude}/skills/hatch-pet"
mkdir -p "$RUN_DIR/final" "$RUN_DIR/qa"

python "$SKILL_DIR/scripts/extract_strip_frames.py" \
  --decoded-dir "$RUN_DIR/decoded" \
  --output-dir "$RUN_DIR/frames" \
  --states all \
  --method auto

python "$SKILL_DIR/scripts/inspect_frames.py" \
  --frames-root "$RUN_DIR/frames" \
  --json-out "$RUN_DIR/qa/review.json" \
  --require-components

python "$SKILL_DIR/scripts/compose_atlas.py" \
  --frames-root "$RUN_DIR/frames" \
  --output "$RUN_DIR/final/spritesheet.png" \
  --webp-output "$RUN_DIR/final/spritesheet.webp"

python "$SKILL_DIR/scripts/validate_atlas.py" \
  "$RUN_DIR/final/spritesheet.webp" \
  --json-out "$RUN_DIR/final/validation.json"

python "$SKILL_DIR/scripts/make_contact_sheet.py" \
  "$RUN_DIR/final/spritesheet.webp" \
  --output "$RUN_DIR/qa/contact-sheet.png"

python "$SKILL_DIR/scripts/render_animation_previews.py" \
  --frames-root "$RUN_DIR/frames" \
  --output-dir "$RUN_DIR/qa/previews"
```

If preview GIFs show extraction-induced size popping (source strip itself was stable), rerun with `--method stable-slots`:

```bash
python "$SKILL_DIR/scripts/extract_strip_frames.py" \
  --decoded-dir "$RUN_DIR/decoded" \
  --output-dir "$RUN_DIR/frames" \
  --states all \
  --method stable-slots

python "$SKILL_DIR/scripts/inspect_frames.py" \
  --frames-root "$RUN_DIR/frames" \
  --json-out "$RUN_DIR/qa/review.json" \
  --require-components \
  --allow-stable-slots
```

### Step 6 — Visual QA

Show the user `qa/contact-sheet.png` and the GIFs in `qa/previews/`. Ask:
> "Check all 9 rows. Do any rows have identity drift, clipped bodies, wrong motion, or visible artifacts?"

If QA passes, continue to packaging.

If a row fails, show the user the specific failure note from `qa/review.json`, then re-present the row's prompt with a repair note appended. Once the user provides a replacement image, overwrite `decoded/<state>.png` and re-run Step 5.

### Step 7 — Package

```bash
RUN_DIR=/absolute/path/to/run
PET_ID=$(jq -r '.pet_id' "$RUN_DIR/pet_request.json")
DISPLAY_NAME=$(jq -r '.display_name' "$RUN_DIR/pet_request.json")
DESCRIPTION=$(jq -r '.description' "$RUN_DIR/pet_request.json")
PET_DIR="${CLAUDE_HOME:-$HOME/.claude}/pets/$PET_ID"
mkdir -p "$PET_DIR"
cp "$RUN_DIR/final/spritesheet.webp" "$PET_DIR/spritesheet.webp"
jq -n \
  --arg id "$PET_ID" \
  --arg displayName "$DISPLAY_NAME" \
  --arg description "$DESCRIPTION" \
  '{id: $id, displayName: $displayName, description: $description, spritesheetPath: "spritesheet.webp"}' \
  > "$PET_DIR/pet.json"
```

```bash
jq -n \
  --arg run_dir "$RUN_DIR" \
  --arg package "$PET_DIR" \
  '{ok: true, run_dir: $run_dir, package: $package}' \
  > "$RUN_DIR/qa/run-summary.json"
```

Report the output paths to the user.

## Image Requirements Summary

When the user asks what images to provide, show this table:

| Image | Format | Size (ChatGPT setting) | Frames | Notes |
|-------|--------|------------------------|--------|-------|
| Base character | PNG | 1024×1024 | 1 | Single centered full-body on green screen |
| idle | PNG | 1792×1024 | 6 | Breathing/blinking loop |
| running-right | PNG | 1792×1024 | 8 | Moving right |
| running-left | PNG | 1792×1024 | 8 | Moving left (or mirrored) |
| waving | PNG | 1792×1024 | 4 | Greeting gesture |
| jumping | PNG | 1792×1024 | 5 | Hop/jump |
| failed | PNG | 1792×1024 | 8 | Sad/deflated reaction |
| waiting | PNG | 1792×1024 | 6 | Expectant pose |
| running | PNG | 1792×1024 | 6 | Focused task work (NOT foot-running) |
| review | PNG | 1792×1024 | 6 | Inspecting/thinking |

Total: 10 images (1 base + 9 rows, or 9 if running-left is mirrored).

Always instruct the user to attach the base character image as a visual reference when generating each row.

## Prompt Requirements for the User

Every prompt must produce:
- A flat solid chroma-key background (default: #00ff00, unless it conflicts with pet colors)
- No text, logos, scenery, UI, shadows, reflections, or floor
- Clean silhouette readable at 192×208 px
- For row strips: frames laid out horizontally side by side, evenly spaced, no borders or guides

## Running-Left Mirror Rule

Only mirror `running-right` when ALL of the following are true:
- No asymmetric markings or prop placement that reads wrong when flipped
- The prop still makes sense on the mirrored side
- Frame timing stays in the same order
- Direction clearly becomes leftward

If the user has any doubt, generate a separate running-left.

## Repair Workflow

If a row fails QA:
1. Show the user the failure note from `qa/review.json`
2. Re-present the row's original prompt with a compact repair note:
   ```
   REPAIR NOTE: <specific issue from review.json>
   Keep everything else identical to the previous generation.
   ```
3. Wait for replacement image
4. Overwrite `decoded/<state>.png`
5. Rerun Step 5 for the full pipeline

For extraction-induced motion popping: do not ask the user for a new image first. Try `--method stable-slots` on the existing decoded file.

## Job Manifest Updates

After copying each received image to its decoded path, mark it complete:

```bash
JOB_ID=<state>
SOURCE=/absolute/path/to/decoded/<state>.png
UPDATED_AT=$(date -u +%Y-%m-%dT%H:%M:%SZ)
TMP=$(mktemp)
jq --arg id "$JOB_ID" --arg source "$SOURCE" --arg at "$UPDATED_AT" \
  '(.jobs[] | select(.id == $id)) += {status: "complete", source_path: $source, completed_at: $at}' \
  "$RUN_DIR/imagegen-jobs.json" > "$TMP"
mv "$TMP" "$RUN_DIR/imagegen-jobs.json"
```

## Acceptance Criteria

- `final/spritesheet.webp` is exactly 1536×1872
- 8 columns × 9 rows, 192×208 px per cell
- Unused cells are fully transparent
- `qa/review.json` has no errors
- Contact sheet and GIF previews reviewed and accepted by user
- `~/.claude/pets/<pet-id>/pet.json` and `spritesheet.webp` written

## Rules

- Never call any image API or generate images programmatically.
- Always wait for the user to provide each image before proceeding.
- Always show the full prompt text for the user to copy.
- Always instruct the user to attach the canonical-base.png when generating rows.
- Only mirror running-left with explicit user confirmation.
- Repair the smallest failing scope first (one row, not the whole sheet).
- Keep the pet's silhouette, palette, style, and props consistent across all rows — treat identity drift as a blocker even if scripts report no errors.
