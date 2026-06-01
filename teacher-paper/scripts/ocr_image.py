#!/usr/bin/env python3
"""
图片文字识别（OCR）兜底器 —— teacher-paper skill 自包含组件

为什么需要它：本 skill 可能运行在**不支持多模态的文本模型**上，或运行环境
没有 Read 多模态识图能力。此时用户提供的截图/拍照无法被模型直接"看懂"，
本脚本用本地 OCR 引擎把图片转成文字，让纯文本模型也能用上图片素材。

识别优先级（自动降级）：
  1. 多模态模型自身识图   —— 若你（调用方）本就能看图，**优先直接识别，不必跑本脚本**
  2. RapidOCR（推荐，纯pip装，离线，中文好）   pip3 install rapidocr-onnxruntime
  3. PaddleOCR（中文最强，体积大）              pip3 install paddleocr
  4. pytesseract（需另装 tesseract 系统程序+中文包）
  全部不可用 → 明确告知，请用户改用支持识图的模型，或手动誊录图中文字

用法：
    python3 ocr_image.py <图片路径> [更多图片 ...]
输出：识别出的纯文本打到 stdout（多图以分隔线隔开）。
建议：识别结果应由调用方存成 materials/ 下的 .md 文件（见 --save 选项）。

    python3 ocr_image.py <图片> --save "<工程>/materials/截图_XX.md"
"""
import sys
import os


def _try_rapidocr(path):
    from rapidocr_onnxruntime import RapidOCR
    engine = RapidOCR()
    result, _ = engine(path)
    if not result:
        return ""
    # result: [[box, text, score], ...]，按出现顺序拼接
    return "\n".join(line[1] for line in result)


def _try_paddleocr(path):
    from paddleocr import PaddleOCR
    ocr = PaddleOCR(use_angle_cls=True, lang="ch", show_log=False)
    result = ocr.ocr(path, cls=True)
    lines = []
    for page in result or []:
        for item in page or []:
            lines.append(item[1][0])
    return "\n".join(lines)


def _try_tesseract(path):
    import pytesseract
    from PIL import Image
    return pytesseract.image_to_string(Image.open(path), lang="chi_sim+eng")


ENGINES = [
    ("RapidOCR", _try_rapidocr, "pip3 install rapidocr-onnxruntime"),
    ("PaddleOCR", _try_paddleocr, "pip3 install paddleocr"),
    ("pytesseract", _try_tesseract,
     "pip3 install pytesseract pillow（并安装 tesseract 与中文语言包 chi_sim）"),
]


def ocr_one(path):
    if not os.path.exists(path):
        return f"[图片不存在] {path}"
    tried = []
    for name, fn, hint in ENGINES:
        try:
            text = fn(path)
            if text and text.strip():
                return f"[OCR引擎:{name}]\n{text.strip()}"
            tried.append(f"{name}:未识别出文字")
        except ImportError:
            tried.append(f"{name}:未安装（{hint}）")
        except Exception as e:
            tried.append(f"{name}:出错（{e}）")
    return ("【OCR 失败】本机没有可用的 OCR 引擎，且当前模型可能无法直接识图。\n"
            "请任选其一：\n"
            "  ① 改用支持多模态（识图）的模型，直接识别图片；\n"
            "  ② 在本机安装任一 OCR 引擎后重试：\n"
            "       pip3 install rapidocr-onnxruntime   （推荐，离线、装得快）\n"
            "  ③ 手动把图片里的文字誊录成 .md 放进 materials/。\n"
            f"（已尝试：{'; '.join(tried)}）")


def main():
    args = [a for a in sys.argv[1:] if not a.startswith("--")]
    save_path = None
    if "--save" in sys.argv:
        i = sys.argv.index("--save")
        if i + 1 < len(sys.argv):
            save_path = sys.argv[i + 1]
            args = [a for a in args if a != save_path]
    if not args:
        print(__doc__)
        sys.exit(1)

    outputs = []
    for p in args:
        outputs.append(f"\n{'='*60}\n# 图片：{os.path.basename(p)}\n{'='*60}")
        outputs.append(ocr_one(p))
    text = "\n".join(outputs)
    print(text)

    if save_path:
        os.makedirs(os.path.dirname(os.path.abspath(save_path)), exist_ok=True)
        with open(save_path, "w", encoding="utf-8") as f:
            f.write(text)
        print(f"\n[已保存] {save_path}")


if __name__ == "__main__":
    main()
