#!/usr/bin/env python3
"""看图工具：描述 / 问答 / OCR（多源自动切换 + 运行时换模型）。
用法:
  python vision.py img.png [-q 问题] [--ocr]      # 看图
  python vision.py /vision-model list             # 列出可用模型
  python vision.py /vision-model zhipu            # 切换默认模型（zen/zhipu/glm/auto）
配置: 同目录 .env 填主源 VISION_* 三行；可选备用源 FALLBACK_* 三行。
主源失败/限流/超时自动切备用源；/vision-model 可强制指定用哪个源。"""
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

MODEL_STATE = Path(__file__).resolve().parent / ".vision-model"
PROVIDERS = {
    "zen": ("VISION_", "OpenCode Zen (mimo-v2.5-free)"),
    "zhipu": ("FALLBACK_", "Zhipu (glm-4.1v-thinking-flash)"),
    "glm": ("FALLBACK_", "Zhipu (glm-4.1v-thinking-flash)"),
}


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


def _provider(prefix):
    key = os.environ.get(prefix + "API_KEY", "").strip()
    base = os.environ.get(prefix + "BASE_URL", "").strip().rstrip("/")
    model = os.environ.get(prefix + "MODEL", "").strip()
    return (key, base, model) if key and base and model else None


def _call(key, base, model, urls, prompt):
    payload = {
        "model": model,
        "messages": [{
            "role": "user",
            "content": [{"type": "text", "text": prompt}] +
                       [{"type": "image_url", "image_url": {"url": u}} for u in urls],
        }],
    }
    last = ""
    for attempt in range(3):
        try:
            r = requests.post(base + "/chat/completions", json=payload,
                              headers={"Authorization": "Bearer " + key}, timeout=180)
            if r.status_code in {429, 500, 502, 503, 504} and attempt < 2:
                time.sleep(2 ** attempt)
                continue
            r.raise_for_status()
            data = r.json()
        except (requests.RequestException, ValueError) as e:
            last = f"请求失败：{e}"
            continue
        try:
            text = data["choices"][0]["message"]["content"]
        except (KeyError, IndexError, TypeError):
            last = "返回格式异常（模型可能不支持图片输入）"
            break
        if isinstance(text, list):
            text = "".join(part.get("text", "") for part in text if isinstance(part, dict))
        text = text.strip()
        if not text:
            last = "返回空内容"
            continue
        return text
    raise RuntimeError(last or "重试次数用尽")


def current_mode():
    if MODEL_STATE.is_file():
        return MODEL_STATE.read_text(encoding="utf-8-sig").strip() or "auto"
    return "auto"


def set_mode(mode):
    MODEL_STATE.write_text(mode, encoding="utf-8")


def ask(urls, prompt):
    if os.environ.get("LANG", "zh").strip().lower() == "zh":
        prompt = f"请使用简体中文回答。\n\n{prompt}"
    mode = current_mode()
    if mode in ("zhipu", "glm"):
        cfg = _provider("FALLBACK_")
        if not cfg:
            sys.exit("备用源未配置：请在 .env 填 FALLBACK_* 三行，或 /vision-model auto 切回自动模式")
        return _call(*cfg, urls, prompt)
    primary = _provider("VISION_")
    if not primary:
        sys.exit("缺少配置：请在 .env 填 VISION_API_KEY / VISION_BASE_URL / VISION_MODEL")
    if mode == "zen":
        return _call(*primary, urls, prompt)
    fallback = _provider("FALLBACK_")
    errors = []
    for name, cfg in (("主源", primary), ("备用源", fallback)):
        if not cfg:
            continue
        try:
            return _call(*cfg, urls, prompt)
        except RuntimeError as e:
            errors.append(f"[{name}] {e}")
    sys.exit("；".join(errors))


def help_text():
    return (
        "可用指令：\n"
        "  /                 显示本帮助\n"
        "  /help             显示本帮助\n"
        "  /vision-model     查看当前视觉模型\n"
        "  /vision-model list   列出可用模型\n"
        "  /vision-model <名>   切换模型（zen / zhipu / glm / auto）\n"
        "  /vision-model auto   恢复自动切换（主源失败走备用，默认）\n"
        "\n"
        "看图：python vision.py 图片.png [-q 问题] [--ocr]\n"
    )


def vision_model_cmd(args):
    if not args:
        print(f"当前模式: {current_mode()}")
        print("用法: /vision-model <zen|zhipu|glm|auto>")
        print("  list   列出可用模型及配置状态")
        print("  zen    用 OpenCode Zen (mimo-v2.5-free)")
        print("  zhipu  用智谱 (glm-4.1v-thinking-flash)")
        print("  glm    zhipu 的别名")
        print("  auto   自动切换（主源失败/限流/超时走备用，默认）")
        return
    arg = args[0].lower()
    if arg == "list":
        for name, (prefix, desc) in PROVIDERS.items():
            if name == "glm":
                continue
            cfg = _provider(prefix)
            print(f"{name}: {desc}  {'已配置' if cfg else '未配置'}")
        return
    if arg == "auto" or arg in PROVIDERS:
        set_mode(arg)
        print(f"视觉模型已切换为: {arg}" + ("（自动切换：主源失败走备用）" if arg == "auto" else f"（{PROVIDERS[arg][1]}）"))
        return
    print(f"未知模型: {arg}，可用: auto / zen / zhipu / glm / list")
    print("输入 /vision-model 查看详细用法")


def main():
    ap = argparse.ArgumentParser(description="看图工具")
    ap.add_argument("images", nargs="+")
    g = ap.add_mutually_exclusive_group()
    g.add_argument("-q", "--query", help="针对图片提问")
    g.add_argument("--ocr", nargs="?", const="", help="逐字转写图中文字")
    args = ap.parse_args()
    load_env()
    if args.images and args.images[0].startswith("/"):
        cmd = args.images[0].lower()
        if cmd in ("/", "/help", "/h"):
            print(help_text())
        elif cmd == "/vision-model":
            vision_model_cmd(args.images[1:])
        else:
            print(f"未知指令: {cmd}")
            print(help_text())
        return
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
