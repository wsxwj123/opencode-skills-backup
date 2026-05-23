#!/usr/bin/env python3
"""Generate a pet image via OpenAI API (gpt-image-1) or local ComfyUI.

Usage:
    python generate_pet_image.py \\
        --prompt-file prompts/base-pet.md \\
        --output decoded/base.png \\
        [--provider openai|comfyui|auto] \\
        [--input-image /path/to/ref.png:role ...] \\
        [--size base|row]

Size presets:
    base  - 1024x1024 square. Uses images.edit when --input-image provided,
            images.generate otherwise.
    row   - 1792x1024 wide landscape for multi-frame sprite strips.
            Always uses images.generate (edit endpoint is square-only).

Provider resolution for 'auto':
    1. HATCH_PET_PROVIDER env var (openai or comfyui)
    2. OPENAI_API_KEY set → openai
    3. ComfyUI reachable at 127.0.0.1:8188 → comfyui
    4. Error

Prints absolute output path to stdout on success.
"""

from __future__ import annotations

import argparse
import base64
import os
import sys
import urllib.request
import urllib.error
from pathlib import Path

COMFYUI_GEN_SCRIPT = "/Users/wsxwj/claudebotlife/scripts/comfyui_gen.py"
COMFYUI_URL = "http://127.0.0.1:8188"

OPENAI_SIZES = {
    "base": "1024x1024",
    "row": "1792x1024",  # wide for multi-frame sprite strips
}

COMFYUI_SIZES = {
    "base": "quick",
    "row": "landscape",
}


# ---------------------------------------------------------------------------
# Provider detection
# ---------------------------------------------------------------------------

def detect_provider() -> str:
    env = os.environ.get("HATCH_PET_PROVIDER", "").lower()
    if env in ("openai", "comfyui"):
        return env
    if os.environ.get("OPENAI_API_KEY"):
        return "openai"
    try:
        urllib.request.urlopen(f"{COMFYUI_URL}/system_stats", timeout=2)
        return "comfyui"
    except (urllib.error.URLError, OSError):
        pass
    print(
        "ERROR: No provider found. Set OPENAI_API_KEY or start ComfyUI, "
        "or set HATCH_PET_PROVIDER=openai|comfyui.",
        file=sys.stderr,
    )
    sys.exit(1)


# ---------------------------------------------------------------------------
# OpenAI provider
# ---------------------------------------------------------------------------

def generate_openai(
    prompt: str,
    input_images: list[Path],
    size: str,
    output: Path,
) -> None:
    try:
        from openai import OpenAI
    except ImportError:
        print("ERROR: openai package not installed. Run: pip install openai", file=sys.stderr)
        sys.exit(1)

    client = OpenAI()
    openai_size = OPENAI_SIZES.get(size, OPENAI_SIZES["base"])

    # Row strips must be wide → always use generate endpoint (edit is square-only).
    # Base images with reference → use edit endpoint for identity grounding.
    use_edit = (size == "base" and input_images)

    if use_edit:
        ref_path = input_images[0]
        # Describe extra refs in text so they inform the prompt.
        extra_desc = ""
        if len(input_images) > 1:
            extra_desc = "\nAdditional visual references: " + ", ".join(
                p.name for p in input_images[1:]
            )
        with open(ref_path, "rb") as f:
            result = client.images.edit(
                model="gpt-image-1",
                image=f,
                prompt=prompt + extra_desc,
                size=openai_size,  # 1024x1024 for edit
            )
    else:
        result = client.images.generate(
            model="gpt-image-1",
            prompt=prompt,
            size=openai_size,
            response_format="b64_json",
        )

    image_data = result.data[0]
    if hasattr(image_data, "b64_json") and image_data.b64_json:
        raw = base64.b64decode(image_data.b64_json)
    elif hasattr(image_data, "url") and image_data.url:
        with urllib.request.urlopen(image_data.url) as resp:
            raw = resp.read()
    else:
        print("ERROR: OpenAI returned no image data.", file=sys.stderr)
        sys.exit(1)

    output.parent.mkdir(parents=True, exist_ok=True)
    output.write_bytes(raw)


# ---------------------------------------------------------------------------
# ComfyUI provider
# ---------------------------------------------------------------------------

def generate_comfyui(prompt: str, size: str, output: Path) -> None:
    import subprocess

    if not Path(COMFYUI_GEN_SCRIPT).exists():
        print(f"ERROR: ComfyUI gen script not found at {COMFYUI_GEN_SCRIPT}", file=sys.stderr)
        sys.exit(1)

    comfyui_size = COMFYUI_SIZES.get(size, COMFYUI_SIZES["base"])
    output.parent.mkdir(parents=True, exist_ok=True)

    cmd = [
        "python3", COMFYUI_GEN_SCRIPT,
        "hatch-pet",
        prompt,
        "--size", comfyui_size,
        "--out", str(output),
    ]
    result = subprocess.run(cmd, capture_output=True, text=True)
    if result.returncode != 0:
        print(f"ERROR: ComfyUI generation failed:\n{result.stderr}", file=sys.stderr)
        sys.exit(1)

    for line in result.stdout.splitlines():
        if line.startswith("MEDIA:"):
            actual = Path(line.split("MEDIA:", 1)[1].strip())
            if actual != output:
                actual.rename(output)
            return
        if line.startswith("FAIL:"):
            print(f"ERROR: {line}", file=sys.stderr)
            sys.exit(1)

    print("ERROR: ComfyUI returned unexpected output.", file=sys.stderr)
    sys.exit(1)


# ---------------------------------------------------------------------------
# Main
# ---------------------------------------------------------------------------

def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--prompt-file", required=True)
    parser.add_argument("--output", required=True)
    parser.add_argument(
        "--provider",
        choices=["openai", "comfyui", "auto"],
        default="auto",
    )
    parser.add_argument(
        "--input-image",
        action="append",
        default=[],
        metavar="PATH[:role]",
        help="Reference image for identity grounding (base size only). Can repeat.",
    )
    parser.add_argument(
        "--size",
        choices=["base", "row"],
        default="base",
        help="base=1024x1024 square, row=1792x1024 wide for sprite strips",
    )
    args = parser.parse_args()

    prompt_path = Path(args.prompt_file)
    if not prompt_path.exists():
        print(f"ERROR: prompt file not found: {prompt_path}", file=sys.stderr)
        sys.exit(1)
    prompt = prompt_path.read_text(encoding="utf-8").strip()

    output = Path(args.output).resolve()

    input_images: list[Path] = []
    for raw in args.input_image:
        path_str = raw.split(":")[0]
        p = Path(path_str)
        if p.exists():
            input_images.append(p)

    provider = args.provider if args.provider != "auto" else detect_provider()

    if provider == "openai":
        generate_openai(prompt, input_images, args.size, output)
    elif provider == "comfyui":
        generate_comfyui(prompt, args.size, output)
    else:
        print(f"ERROR: unknown provider: {provider}", file=sys.stderr)
        sys.exit(1)

    print(str(output))


if __name__ == "__main__":
    main()
