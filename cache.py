#!/usr/bin/env python3
"""磁盘缓存：图指纹 -> 描述文本。同图同问秒回，支持上限控制与历史翻看。
纯标准库实现（json + hashlib），无第三方依赖。
"""
import hashlib
import json
import os
import time
from pathlib import Path

DEFAULT_LIMIT = 200 * 1024 * 1024  # 200MB
CACHE_DIR = Path(__file__).resolve().parent / ".vision_cache"
INDEX_FILE = CACHE_DIR / "index.json"

_index = None
_index_mtime = 0.0


def _load_index():
    global _index, _index_mtime
    if _index is None or (INDEX_FILE.exists() and INDEX_FILE.stat().st_mtime > _index_mtime):
        if INDEX_FILE.exists():
            try:
                _index = json.loads(INDEX_FILE.read_text(encoding="utf-8"))
            except Exception:
                _index = {}
        else:
            _index = {}
        _index_mtime = INDEX_FILE.stat().st_mtime if INDEX_FILE.exists() else 0.0
    return _index


def _save_index():
    CACHE_DIR.mkdir(parents=True, exist_ok=True)
    INDEX_FILE.write_text(json.dumps(_index, ensure_ascii=False), encoding="utf-8")


def fingerprint(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest()


def entry_key(fp: str, prompt: str) -> str:
    return fp + "::" + hashlib.sha256(prompt.encode("utf-8")).hexdigest()[:16]


def get(fp: str, prompt: str):
    idx = _load_index()
    return idx.get(entry_key(fp, prompt))


def put(fp: str, prompt: str, description: str):
    idx = _load_index()
    idx[entry_key(fp, prompt)] = {
        "t": int(time.time()),
        "d": description,
        "p": prompt[:80],
    }
    _save_index()
    _enforce_limit()


def _enforce_limit():
    idx = _load_index()
    if INDEX_FILE.stat().st_size <= DEFAULT_LIMIT:
        return
    # 超限：按时间升序删最旧的，直到回到 60% 占用
    entries = sorted(idx.items(), key=lambda kv: kv[1].get("t", 0))
    target = DEFAULT_LIMIT * 0.6
    for k, _ in entries:
        if INDEX_FILE.stat().st_size <= target:
            break
        idx.pop(k)
        _save_index()


def list_entries(limit=20):
    idx = _load_index()
    entries = sorted(idx.items(), key=lambda kv: kv[1].get("t", 0), reverse=True)
    out = []
    for k, v in entries[:limit]:
        fp = k.split("::")[0]
        out.append((fp, v.get("t", 0), v.get("d", ""), v.get("p", "")))
    return out


def clear():
    global _index
    _index = {}
    if INDEX_FILE.exists():
        INDEX_FILE.unlink()
    return True


def info():
    idx = _load_index()
    size = INDEX_FILE.stat().st_size if INDEX_FILE.exists() else 0
    return {"entries": len(idx), "size_mb": round(size / 1024 / 1024, 2), "limit_mb": 200}
