#!/usr/bin/env python3
"""MCP server: expose vision.py as describe_image / ocr_image (FastMCP, stdio)."""
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))

import vision  # noqa: E402

from mcp.server.fastmcp import FastMCP  # noqa: E402

vision.load_env()

mcp = FastMCP(
    "vision",
    instructions=(
        "Tools that give the model vision by converting images into text "
        "descriptions or verbatim OCR via a multimodal API."
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


if __name__ == "__main__":
    mcp.run()
