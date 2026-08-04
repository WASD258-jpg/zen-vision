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

import cache

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


def _providers():
    """按优先级返回所有已配置源: [(id, key, base, model), ...]
    主源 VISION_ -> 备用 FALLBACK_ -> VISION3_ -> VISION4_ -> ...
    """
    result = []
    prim = _provider("VISION_")
    if prim:
        result.append(("zen", *prim))
    fb = _provider("FALLBACK_")
    if fb:
        result.append(("zhipu", *fb))
    i = 3
    while True:
        p = _provider(f"VISION{i}_")
        if p:
            result.append((f"v{i}", *p))
            i += 1
        else:
            break
    return result


def _provider_by_id(mode):
    """按模式 id 找到对应 provider 配置。"""
    if mode in ("zhipu", "glm"):
        return "FALLBACK_", _provider("FALLBACK_")
    if mode == "zen":
        return "VISION_", _provider("VISION_")
    if mode.startswith("v") and mode[1:].isdigit():
        prefix = f"VISION{mode[1:]}_"
        return prefix, _provider(prefix)
    return None, None


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
    cached = _cache_get(urls, prompt)
    if cached is not None:
        return cached
    mode = current_mode()
    if mode != "auto":
        _, cfg = _provider_by_id(mode)
        if not cfg:
            sys.exit(f"源 {mode} 未配置：请在 .env 填对应 VISION/FALLBACK 配置，或 /vision-model auto 切回自动模式")
        return _cache_put(urls, prompt, _call(*cfg, urls, prompt))
    providers = _providers()
    if not providers:
        sys.exit("缺少配置：请在 .env 填 VISION_API_KEY / VISION_BASE_URL / VISION_MODEL")
    errors = []
    for pid, *cfg in providers:
        try:
            return _cache_put(urls, prompt, _call(*cfg, urls, prompt))
        except RuntimeError as e:
            errors.append(f"[{pid}] {e}")
    sys.exit("；".join(errors))


def _cache_key(urls, prompt):
    if len(urls) != 1:
        return None
    fp = cache.fingerprint(urls[0].encode("utf-8"))
    return fp, prompt


def _cache_get(urls, prompt):
    key = _cache_key(urls, prompt)
    if not key:
        return None
    hit = cache.get(*key)
    if hit:
        return hit["d"]
    return None


def _cache_put(urls, prompt, text):
    key = _cache_key(urls, prompt)
    if key:
        cache.put(*key, text)
    return text


def help_text():
    return (
        "可用指令：\n"
        "  /                    显示本帮助\n"
        "  /help                显示本帮助\n"
        "  /vision-model        查看当前视觉模型\n"
        "  /vision-model list   列出所有已配置模型\n"
        "  /vision-model <名>   切换模型（zen / zhipu / glm / v3 / v4 ... / auto）\n"
        "  /vision-model auto   恢复自动切换（按序 fallback，默认）\n"
        "  /cache               查看缓存统计\n"
        "  /cache list          列出最近缓存（翻看历史描述）\n"
        "  /cache clear         清空缓存\n"
        "\n"
        "看图：python vision.py 图片.png [-q 问题] [--ocr]\n"
    )


def cache_cmd(args):
    if not args:
        info = cache.info()
        print(f"缓存: {info['entries']} 条, {info['size_mb']} MB / 上限 {info['limit_mb']} MB")
        return
    arg = args[0].lower()
    if arg == "list":
        entries = cache.list_entries(20)
        if not entries:
            print("缓存为空。")
            return
        print(f"最近 {len(entries)} 条（时间倒序）：")
        for fp, t, desc, prompt in entries:
            ts = time.strftime("%m-%d %H:%M", time.localtime(t))
            print(f"  [{ts}] {desc[:60]}")
        return
    if arg == "clear":
        cache.clear()
        print("缓存已清空。")
        return
    print(f"未知参数: {arg}，可用: list / clear（无参数 = 统计）")


def vision_model_cmd(args):
    if not args:
        print(f"当前模式: {current_mode()}")
        print("用法: /vision-model <zen|zhipu|glm|v3|v4|...|auto>")
        print("  list   列出所有已配置模型")
        print("  zen    用 OpenCode Zen (mimo-v2.5-free)")
        print("  zhipu  用智谱 (glm-4.1v-thinking-flash)")
        print("  glm    zhipu 的别名")
        print("  v3/v4  额外源（在 .env 填 VISION3_*/VISION4_* 后可用）")
        print("  auto   自动切换（主源失败/限流/超时按序走备用，默认）")
        return
    arg = args[0].lower()
    if arg == "list":
        providers = _providers()
        if not providers:
            print("尚未配置任何模型源。")
            return
        for pid, _key, _base, model in providers:
            print(f"{pid}: {model}")
        return
    valid = None
    if arg == "auto" or arg in ("zen", "zhipu", "glm") or (arg.startswith("v") and arg[1:].isdigit()):
        set_mode(arg)
        desc = "自动切换（按序 fallback）" if arg == "auto" else arg
        print(f"视觉模型已切换为: {arg}（{desc}）")
        return
    print(f"未知模型: {arg}，可用: auto / zen / zhipu / glm / v3 / v4 ... / list")
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
        elif cmd == "/cache":
            cache_cmd(args.images[1:])
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
