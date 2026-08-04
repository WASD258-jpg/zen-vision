#!/usr/bin/env python3
"""MCP server: expose vision.py as describe_image / ocr_image (FastMCP, stdio)."""
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))

import time  # noqa: E402

import vision  # noqa: E402
import watch  # noqa: E402
import cache  # noqa: E402

from mcp.server.fastmcp import FastMCP  # noqa: E402

vision.load_env()

mcp = FastMCP(
    "vision",
    instructions=(
        "Tools that give the model vision by converting images into text "
        "descriptions or verbatim OCR via a multimodal API. "
        "Use describe_image / ocr_image to look at images; use "
        "set_vision_model to switch between vision sources "
        "(zen = OpenCode Zen default, zhipu/glm = Zhipu fallback, auto = auto-failover); "
        "use watch_screen / watch_video to monitor the screen or a video and "
        "describe what changes."
    ),
)


@mcp.tool()
def describe_image(path: str, query: str = "") -> str:
    """Describe the image at `path`, or answer `query` about it.
    path: absolute path to a local image (PNG/JPEG/GIF/WebP)."""
    try:
        return vision.ask([vision.data_url(path)], query or "请详细描述这张图片的内容。")
    except BaseException as exc:
        return f"error: {exc}"


@mcp.tool()
def ocr_image(path: str) -> str:
    """Transcribe every piece of visible text in the image verbatim (OCR).
    path: absolute path to a local image (PNG/JPEG/GIF/WebP)."""
    try:
        return vision.ask([vision.data_url(path)], vision.OCR_PROMPT)
    except BaseException as exc:
        return f"error: {exc}"


@mcp.tool()
def set_vision_model(model: str = "") -> str:
    """Query or switch the vision model source.
    model: 'zen' (OpenCode Zen, default) / 'zhipu' or 'glm' (Zhipu fallback) /
           'auto' (auto-failover: primary -> fallback). Empty = query current."""
    try:
        if not model:
            return f"当前视觉模型: {vision.current_mode()}"
        if model not in ("auto", "zen", "zhipu", "glm"):
            return f"未知模型: {model}，可用: auto / zen / zhipu / glm"
        vision.set_mode(model)
        return f"视觉模型已切换为: {model}"
    except BaseException as exc:
        return f"error: {exc}"


def _fmt_changes(results):
    if not results:
        return "监控期间画面无变化。"
    lines = [f"检测到 {len(results)} 次画面变化："]
    lines += [f"[{t}] {d}" for t, d in results]
    return "\n".join(lines)


@mcp.tool()
def watch_screen(duration: int = 30, interval: float = 1.0, threshold: float = 8.0, query: str = "") -> str:
    """Monitor the screen for `duration` seconds and describe detected changes.
    Args: duration (seconds, default 30), interval (sampling seconds, default 1),
    threshold (change sensitivity 0-255, default 8), query (custom prompt).
    Returns a list of change events with timestamps."""
    try:
        from PIL import ImageGrab
        results = watch.collect_changes(
            lambda: ImageGrab.grab(),
            duration=duration, interval=interval, threshold=threshold, query=query or None,
        )
        return _fmt_changes(results)
    except BaseException as exc:
        return f"error: {exc}"


@mcp.tool()
def watch_video(path: str, every: float = 1.0, threshold: float = 8.0, query: str = "") -> str:
    """Analyze a video file and describe detected scene changes.
    Args: path (video file), every (sampling seconds, default 1),
    threshold (change sensitivity 0-255, default 8), query (custom prompt).
    Returns a list of change events with timestamps."""
    try:
        import cv2
        from PIL import Image
        cap = cv2.VideoCapture(path)
        if not cap.isOpened():
            return f"error: 无法打开视频 {path}"
        fps = cap.get(cv2.CAP_PROP_FPS) or 30
        total = int(cap.get(cv2.CAP_PROP_FRAME_COUNT))
        step = max(1, int(round(fps * every)))

        def grab():
            for _ in range(step):
                ret, frame = cap.read()
                if not ret:
                    return None
            return Image.fromarray(frame[:, :, ::-1])

        try:
            results = watch.collect_changes(
                grab, duration=total / fps, interval=0, threshold=threshold, query=query or None,
            )
        finally:
            cap.release()
        return _fmt_changes(results)
    except BaseException as exc:
        return f"error: {exc}"


@mcp.tool()
def cache_list(limit: int = 10) -> str:
    """List recent cached vision descriptions (browse analysis history).
    Args: limit (max entries, default 10).
    Returns entries with timestamps, newest first."""
    try:
        entries = cache.list_entries(limit)
        if not entries:
            return "缓存为空。"
        lines = [f"最近 {len(entries)} 条（时间倒序）："]
        for _fp, t, desc, _prompt in entries:
            ts = time.strftime("%m-%d %H:%M", time.localtime(t))
            lines.append(f"[{ts}] {desc[:80]}")
        return "\n".join(lines)
    except BaseException as exc:
        return f"error: {exc}"


@mcp.tool()
def cache_clear() -> str:
    """Clear the vision disk cache (all stored descriptions)."""
    try:
        cache.clear()
        return "缓存已清空。"
    except BaseException as exc:
        return f"error: {exc}"


if __name__ == "__main__":
    mcp.run()
