#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""作文评分 skill 的文本提取入口：只做 ①文件预检 ②图片OCR。

职责边界（INTERFACE E4/E5）：本脚本不做 PDF/Word 提取。PDF/Word 预检通过后
输出路由提示，由 SKILL.md 引导 Claude 按 pdf/docx 技能提取。txt/md 直接回读内容。

用法：python3 extract_text.py <路径>
退出码：0=成功（stdout=提取文本/路由提示）；1=OCR失败（E4）；2=预检失败（E2/E3）。
只读不写盘；子进程一律参数数组传参（禁字符串拼接，防注入）。
"""
import os
import subprocess
import sys

SUPPORTED = {"txt", "md", "png", "jpg", "jpeg", "pdf", "docx"}
IMAGES = {"png", "jpg", "jpeg"}
EXT_TEXT = {"txt", "md"}


def fail(msg, code):
    print(msg)
    sys.exit(code)


def precheck(path):
    """E2 三态 + E3，任一失败即输出契约文案并退出。"""
    if not os.path.exists(path):
        fail(f"文件不存在：{path}", 2)
    if os.path.isdir(path):
        fail(f"{path}是目录，请给文件", 2)
    if not os.access(path, os.R_OK):
        fail(f"无法读取：{path}（权限不足）", 2)
    ext = os.path.splitext(path)[1].lstrip(".").lower()
    if ext not in SUPPORTED:
        fail(f"不支持的文件类型：{ext}。支持：txt/md/png/jpg/jpeg/pdf/docx", 2)
    return ext


def ocr(path):
    """本机 tesseract chi_sim OCR，失败输出 E4 文案。"""
    try:
        proc = subprocess.run(
            ["tesseract", path, "stdout", "-l", "chi_sim"],
            capture_output=True, text=True, errors="replace", timeout=180,
        )
    except FileNotFoundError:
        fail("OCR失败：未找到 tesseract（请先安装 tesseract 及 chi_sim 语言包）", 1)
    except subprocess.TimeoutExpired:
        fail("OCR失败：tesseract 处理超时", 1)
    if proc.returncode != 0:
        fail(f"OCR失败：{proc.stderr.strip()}", 1)
    text = proc.stdout.strip()
    if not text:
        fail("OCR失败：图片中未识别到文字，建议粘贴文本", 1)
    print(text)
    sys.exit(0)


def main():
    if len(sys.argv) != 2:
        fail("用法：python3 extract_text.py <文件路径>", 2)
    path = sys.argv[1]
    ext = precheck(path)
    if ext in IMAGES:
        ocr(path)
    if ext in ("pdf", "docx"):
        print(f"PDF/Word 提取请使用 pdf/docx 技能处理：{path}")
        sys.exit(0)
    # txt / md
    with open(path, encoding="utf-8", errors="replace") as f:
        sys.stdout.write(f.read())


if __name__ == "__main__":
    main()
