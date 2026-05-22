---
name: hivision-idphotos
description: Use when users ask to process ID photos with HivisionIDPhotos for matting, background replacement, size crop, or print layout generation.
---

# Hivision ID Photo Processor

## Overview

Task skill for executing HivisionIDPhotos image workflows from terminal commands.
This skill is for real processing outputs, not repository analysis.

## When to Use

Use this skill when user requests include:
- Modify ID photo / 修改证件照
- Cutout / 抠图
- Change background color / 换底色
- Replace background / 换背景
- Crop to standard size / 裁剪
- Generate print layout / 排版
- Remove background / portrait matting
- Change ID photo background color
- Crop to passport or visa size
- Generate print layout sheets (6-inch / 5-inch / A4 style by size settings)
- End-to-end pipeline from raw portrait to final files

Do not use this skill for generic Photoshop editing or non-ID-photo composition work.

## Trigger Examples (Natural Language)

The following user phrases should trigger this skill:
- `修改证件照`
- `证件照抠图`
- `证件照换底色`
- `证件照换背景`
- `证件照裁剪成1寸`
- `证件照排版`
- `把这张照片做成证件照`

## Required Inputs

- `input` image path
- `outdir` output directory
- `width` and `height` in pixels (default `295x413`)
- optional `bg_color` in hex without `#` (default `638cce`)

## Command Entry

Run the wrapper script:

```bash
python3 scripts/hivision_task.py <command> [options]
```

Commands:
- `pipeline`: matting -> crop -> background -> layout
- `matting`: output transparent png
- `crop`: crop transparent id photo by size
- `background`: apply pure/gradient background to RGBA image
- `layout`: generate print layout from final ID photo

## Typical Usage

```bash
python3 scripts/hivision_task.py pipeline \
  --input /abs/path/photo.jpg \
  --outdir /abs/path/out \
  --width 295 --height 413 \
  --bg-color 438edb \
  --render 0
```

Expected outputs in `outdir`:
- `idphoto_matting.png`
- `idphoto_crop.png`
- `idphoto_crop_hd.png`
- `idphoto_bg.jpg`
- `idphoto_layout.jpg`

## Environment Notes

- By default wrapper reads repo path from `HIVISION_REPO`.
- Default repo path: `/Users/wsxwj/.codex/skills/hivision-idphotos/vendor/HivisionIDPhotos`
- Ensure model weights exist under:
  - `hivision/creator/weights/`
  - (optional) `hivision/creator/retinaface/weights/`

If model files are missing, download them with the upstream repo script:
`python3 scripts/download_model.py --models hivision_modnet`
