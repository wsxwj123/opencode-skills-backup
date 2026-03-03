#!/usr/bin/env python3
"""Task wrapper for HivisionIDPhotos inference.py."""

from __future__ import annotations

import argparse
import os
import subprocess
import sys
from pathlib import Path
import cv2
import numpy as np


DEFAULT_REPO = "/Users/wsxwj/.codex/skills/hivision-idphotos/vendor/HivisionIDPhotos"


def resolve_repo(repo_arg: str | None) -> Path:
    repo = Path(repo_arg or os.environ.get("HIVISION_REPO", DEFAULT_REPO)).expanduser()
    if not repo.exists():
        raise FileNotFoundError(f"Hivision repo not found: {repo}")
    inference = repo / "inference.py"
    if not inference.exists():
        raise FileNotFoundError(f"inference.py not found in repo: {repo}")
    return repo


def run_inference(repo: Path, args: list[str]) -> None:
    cmd = ["python3", "inference.py", *args]
    print("Running:", " ".join(cmd))
    subprocess.run(cmd, cwd=str(repo), check=True)


def _hex_to_bgr(hex_color: str) -> tuple[int, int, int]:
    s = hex_color.strip().lstrip("#")
    if len(s) != 6:
        raise ValueError(f"Invalid hex color: {hex_color}")
    r = int(s[0:2], 16)
    g = int(s[2:4], 16)
    b = int(s[4:6], 16)
    return (b, g, r)


def _build_background(h: int, w: int, bgr: tuple[int, int, int], render: int) -> np.ndarray:
    base = np.zeros((h, w, 3), dtype=np.float32)
    if render == 0:
        base[:] = bgr
        return base

    if render == 1:
        grad = np.linspace(0.9, 1.1, h, dtype=np.float32).reshape(h, 1, 1)
        base[:] = np.array(bgr, dtype=np.float32)
        return np.clip(base * grad, 0, 255)

    y, x = np.ogrid[:h, :w]
    cy, cx = h / 2.0, w / 2.0
    dist = np.sqrt((x - cx) ** 2 + (y - cy) ** 2)
    dist = dist / (dist.max() + 1e-6)
    factor = (1.1 - 0.2 * dist).astype(np.float32)[..., None]
    base[:] = np.array(bgr, dtype=np.float32)
    return np.clip(base * factor, 0, 255)


def _write_image_unicode(path: str, image_bgr: np.ndarray, quality: int = 95) -> None:
    ok, buf = cv2.imencode(".jpg", image_bgr, [int(cv2.IMWRITE_JPEG_QUALITY), quality])
    if not ok:
        raise RuntimeError("Failed to encode image")
    with open(path, "wb") as f:
        f.write(buf.tobytes())


def ensure_outdir(path: str) -> Path:
    outdir = Path(path).expanduser()
    outdir.mkdir(parents=True, exist_ok=True)
    return outdir


def add_common_image_args(p: argparse.ArgumentParser) -> None:
    p.add_argument("--repo", help="HivisionIDPhotos repository path")
    p.add_argument("--input", required=True, help="Input image path")
    p.add_argument("--output", required=True, help="Output image path")
    p.add_argument("--width", type=int, default=295, help="Output width in px")
    p.add_argument("--height", type=int, default=413, help="Output height in px")
    p.add_argument(
        "--matting-model",
        default="hivision_modnet",
        choices=[
            "hivision_modnet",
            "modnet_photographic_portrait_matting",
            "mnn_hivision_modnet",
            "rmbg-1.4",
            "birefnet-v1-lite",
        ],
    )
    p.add_argument(
        "--face-detect-model",
        default="mtcnn",
        choices=["mtcnn", "face_plusplus", "retinaface-resnet50"],
    )
    p.add_argument("--dpi", type=int, default=300)
    p.add_argument("--kb", type=int, default=None)


def cmd_matting(ns: argparse.Namespace) -> None:
    repo = resolve_repo(ns.repo)
    run_inference(
        repo,
        [
            "-t",
            "human_matting",
            "-i",
            ns.input,
            "-o",
            ns.output,
            "--matting_model",
            ns.matting_model,
            "--face_detect_model",
            ns.face_detect_model,
        ],
    )


def cmd_crop(ns: argparse.Namespace) -> None:
    repo = resolve_repo(ns.repo)
    run_inference(
        repo,
        [
            "-t",
            "idphoto_crop",
            "-i",
            ns.input,
            "-o",
            ns.output,
            "--width",
            str(ns.width),
            "--height",
            str(ns.height),
            "--matting_model",
            ns.matting_model,
            "--face_detect_model",
            ns.face_detect_model,
            "--dpi",
            str(ns.dpi),
        ],
    )


def cmd_background(ns: argparse.Namespace) -> None:
    _ = resolve_repo(ns.repo)
    img = cv2.imread(ns.input, cv2.IMREAD_UNCHANGED)
    if img is None:
        raise FileNotFoundError(f"Cannot read input image: {ns.input}")
    if img.ndim != 3 or img.shape[2] != 4:
        raise ValueError("background command expects a 4-channel RGBA/BGRA input image")

    fg = img[:, :, :3].astype(np.float32)
    alpha = (img[:, :, 3:4].astype(np.float32)) / 255.0
    bgr = _hex_to_bgr(ns.bg_color)
    bg = _build_background(img.shape[0], img.shape[1], bgr, ns.render)
    result = (fg * alpha + bg * (1.0 - alpha)).clip(0, 255).astype(np.uint8)
    _write_image_unicode(ns.output, result)


def cmd_layout(ns: argparse.Namespace) -> None:
    repo = resolve_repo(ns.repo)
    args = [
        "-t",
        "generate_layout_photos",
        "-i",
        ns.input,
        "-o",
        ns.output,
        "--width",
        str(ns.width),
        "--height",
        str(ns.height),
        "--dpi",
        str(ns.dpi),
    ]
    if ns.kb:
        args.extend(["-k", str(ns.kb)])
    run_inference(repo, args)


def cmd_pipeline(ns: argparse.Namespace) -> None:
    repo = resolve_repo(ns.repo)
    outdir = ensure_outdir(ns.outdir)

    matting = outdir / "idphoto_matting.png"
    crop = outdir / "idphoto_crop.png"
    bg = outdir / "idphoto_bg.jpg"
    layout = outdir / "idphoto_layout.jpg"

    run_inference(
        repo,
        [
            "-t",
            "human_matting",
            "-i",
            ns.input,
            "-o",
            str(matting),
            "--matting_model",
            ns.matting_model,
            "--face_detect_model",
            ns.face_detect_model,
        ],
    )
    run_inference(
        repo,
        [
            "-t",
            "idphoto_crop",
            "-i",
            str(matting),
            "-o",
            str(crop),
            "--width",
            str(ns.width),
            "--height",
            str(ns.height),
            "--matting_model",
            ns.matting_model,
            "--face_detect_model",
            ns.face_detect_model,
            "--dpi",
            str(ns.dpi),
        ],
    )

    class _BGArgs:
        pass

    bg_ns = _BGArgs()
    bg_ns.repo = str(repo)
    bg_ns.input = str(crop)
    bg_ns.output = str(bg)
    bg_ns.bg_color = ns.bg_color
    bg_ns.render = ns.render
    bg_ns.dpi = ns.dpi
    bg_ns.kb = ns.kb
    cmd_background(bg_ns)

    layout_args = [
        "-t",
        "generate_layout_photos",
        "-i",
        str(bg),
        "-o",
        str(layout),
        "--width",
        str(ns.width),
        "--height",
        str(ns.height),
        "--dpi",
        str(ns.dpi),
    ]
    if ns.kb:
        layout_args.extend(["-k", str(ns.kb)])
    run_inference(repo, layout_args)

    print("Pipeline done. Outputs:")
    print(f"- {matting}")
    print(f"- {crop}")
    print(f"- {crop.with_name(crop.stem + '_hd' + crop.suffix)}")
    print(f"- {bg}")
    print(f"- {layout}")


def build_parser() -> argparse.ArgumentParser:
    p = argparse.ArgumentParser(description="Hivision ID photo task wrapper")
    sub = p.add_subparsers(dest="command", required=True)

    mat = sub.add_parser("matting", help="Remove background, output RGBA png")
    add_common_image_args(mat)
    mat.set_defaults(func=cmd_matting)

    crop = sub.add_parser("crop", help="Crop transparent ID photo to size")
    add_common_image_args(crop)
    crop.set_defaults(func=cmd_crop)

    bg = sub.add_parser("background", help="Add background color/gradient")
    bg.add_argument("--repo", help="HivisionIDPhotos repository path")
    bg.add_argument("--input", required=True, help="Input RGBA image path")
    bg.add_argument("--output", required=True, help="Output image path")
    bg.add_argument("--bg-color", default="638cce", help="Hex color without #")
    bg.add_argument("--render", type=int, choices=[0, 1, 2], default=0)
    bg.add_argument("--dpi", type=int, default=300)
    bg.add_argument("--kb", type=int, default=None)
    bg.set_defaults(func=cmd_background)

    layout = sub.add_parser("layout", help="Generate print layout")
    layout.add_argument("--repo", help="HivisionIDPhotos repository path")
    layout.add_argument("--input", required=True, help="Input 3-channel image path")
    layout.add_argument("--output", required=True, help="Output layout image path")
    layout.add_argument("--width", type=int, default=295, help="Single photo width in px")
    layout.add_argument("--height", type=int, default=413, help="Single photo height in px")
    layout.add_argument("--dpi", type=int, default=300)
    layout.add_argument("--kb", type=int, default=None)
    layout.set_defaults(func=cmd_layout)

    pipe = sub.add_parser("pipeline", help="Full process: matting->crop->bg->layout")
    pipe.add_argument("--repo", help="HivisionIDPhotos repository path")
    pipe.add_argument("--input", required=True, help="Input portrait image path")
    pipe.add_argument("--outdir", required=True, help="Output directory")
    pipe.add_argument("--width", type=int, default=295, help="ID photo width in px")
    pipe.add_argument("--height", type=int, default=413, help="ID photo height in px")
    pipe.add_argument("--bg-color", default="638cce", help="Hex color without #")
    pipe.add_argument("--render", type=int, choices=[0, 1, 2], default=0)
    pipe.add_argument("--dpi", type=int, default=300)
    pipe.add_argument("--kb", type=int, default=None)
    pipe.add_argument(
        "--matting-model",
        default="hivision_modnet",
        choices=[
            "hivision_modnet",
            "modnet_photographic_portrait_matting",
            "mnn_hivision_modnet",
            "rmbg-1.4",
            "birefnet-v1-lite",
        ],
    )
    pipe.add_argument(
        "--face-detect-model",
        default="mtcnn",
        choices=["mtcnn", "face_plusplus", "retinaface-resnet50"],
    )
    pipe.set_defaults(func=cmd_pipeline)

    return p


def main() -> int:
    parser = build_parser()
    ns = parser.parse_args()
    try:
        ns.func(ns)
    except subprocess.CalledProcessError as exc:
        print(f"Command failed with exit code {exc.returncode}", file=sys.stderr)
        return exc.returncode
    except Exception as exc:  # noqa: BLE001
        print(f"Error: {exc}", file=sys.stderr)
        return 1
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
