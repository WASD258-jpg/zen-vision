#!/usr/bin/env python3
"""看图工具：描述 / 问答 / OCR。
用法: python vision.py img.png [-q 问题] [--ocr]
配置: 同目录 .env 填 VISION_API_KEY / VISION_BASE_URL / VISION_MODEL"""
import argparse
import base64
import mimetypes
import os
import sys
import time
from pathlib import Path

import requests

OCR_PROMPT = (
    "Transcribe every piece of visible text in this image verbatim "
    "(titles, body text, labels, watermarks, etc.), line by line, "
    "without omitting any characters. Do not rewrite, summarize, or translate. No preamble."
)


def load_env():
    env_path = Path(__file__).resolve().parent / ".env"
    if env_path.is_file():
        for raw in env_path.read_text(encoding="utf-8-sig").splitlines():
            line = raw.strip()
            if line and not line.startswith("#") and "=" in line:
                k, _, v = line.partition("=")
                os.environ.setdefault(k.strip(), v.strip().strip('"').strip("'"))


def data_url(path):
    p = Path(path).expanduser()
    if not p.is_file():
        sys.exit(f"图片不存在: {p}")
    mime, _ = mimetypes.guess_type(p.name)
    if mime not in {"image/png", "image/jpeg", "image/gif", "image/webp"}:
        sys.exit("仅支持 PNG/JPEG/GIF/WebP")
    return f"data:{mime};base64," + base64.b64encode(p.read_bytes()).decode()


def ask(urls, prompt):
    key = os.environ.get("VISION_API_KEY", "").strip()
    base = os.environ.get("VISION_BASE_URL", "").strip().rstrip("/")
    model = os.environ.get("VISION_MODEL", "").strip()
    if not (key and base and model):
        sys.exit("缺少配置：请在 .env 填 VISION_API_KEY / VISION_BASE_URL / VISION_MODEL")
    if os.environ.get("LANG", "zh").strip().lower() == "zh":
        prompt = f"请使用简体中文回答。\n\n{prompt}"
    payload = {
        "model": model,
        "messages": [{
            "role": "user",
            "content": [{"type": "text", "text": prompt}] +
                       [{"type": "image_url", "image_url": {"url": u}} for u in urls],
        }],
    }
    try:
        for attempt in range(3):
            r = requests.post(base + "/chat/completions", json=payload,
                              headers={"Authorization": "Bearer " + key}, timeout=180)
            if r.status_code in {429, 500, 502, 503, 504} and attempt < 2:
                time.sleep(2 ** attempt)
                continue
            r.raise_for_status()
            break
        data = r.json()
    except (requests.RequestException, ValueError) as e:
        detail = getattr(e, "response", None)
        body = ""
        if detail is not None:
            body = detail.text[:300].replace("\n", " ")
        sys.exit(f"请求失败：{e}" + (f" | {body}" if body else ""))
    try:
        text = data["choices"][0]["message"]["content"]
    except (KeyError, IndexError, TypeError):
        sys.exit("返回格式异常：请确认 VISION_MODEL 是支持图片的多模态模型（如 mimo-v2.5-free）")
    if isinstance(text, list):
        text = "".join(part.get("text", "") for part in text if isinstance(part, dict))
    return text.strip()


def main():
    ap = argparse.ArgumentParser(description="看图工具")
    ap.add_argument("images", nargs="+")
    g = ap.add_mutually_exclusive_group()
    g.add_argument("-q", "--query", help="针对图片提问")
    g.add_argument("--ocr", nargs="?", const="", help="逐字转写图中文字")
    args = ap.parse_args()
    load_env()
    urls = [data_url(p) for p in args.images]
    if args.ocr is not None:
        prompt = OCR_PROMPT + (f" 额外要求：{args.ocr}" if args.ocr else "")
    elif args.query:
        prompt = args.query
    elif len(urls) > 1:
        prompt = "Describe each image in detail (label them Image 1, Image 2, ...), then point out the notable differences between them."
    else:
        prompt = "请详细描述这张图片的内容。"
    print(ask(urls, prompt))


if __name__ == "__main__":
    main()
