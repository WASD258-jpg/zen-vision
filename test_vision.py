#!/usr/bin/env python3
"""最小本地测试：不调任何 API，验证核心逻辑。
运行: python -m unittest test_vision -v
"""
import os
import sys
import tempfile
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parent
sys.path.insert(0, str(ROOT))


class TestSpatialPrompt(unittest.TestCase):
    def test_default_prompt_has_spatial_terms(self):
        import vision
        # 通过 CLI 路径触发默认 prompt 的构造逻辑：
        # 直接在源码里确认空间提示词存在（避免模拟完整 CLI）
        src = (ROOT / "vision.py").read_text(encoding="utf-8")
        self.assertIn("九宫格", src)
        self.assertIn("相对坐标", src)
        self.assertIn("请详细描述这张图片的内容", src)

    def test_watch_prompt_has_spatial_terms(self):
        src = (ROOT / "watch.py").read_text(encoding="utf-8")
        self.assertIn("九宫格", src)
        self.assertIn("相对位置", src)


class TestCache(unittest.TestCase):
    def test_cache_roundtrip_and_clear(self):
        import cache
        tmp = Path(tempfile.mkdtemp())
        # 临时换缓存目录
        cache.CACHE_DIR = tmp
        cache.INDEX_FILE = tmp / "index.json"
        cache.clear()
        fp = cache.fingerprint(b"hello world")
        self.assertEqual(len(fp), 64)
        self.assertIsNone(cache.get(fp, "q"))
        cache.put(fp, "q", "desc")
        hit = cache.get(fp, "q")
        self.assertIsNotNone(hit)
        self.assertEqual(hit["d"], "desc")
        cache.clear()
        self.assertIsNone(cache.get(fp, "q"))


class TestWatchMad(unittest.TestCase):
    def test_mad_values(self):
        import watch
        from PIL import Image
        a = Image.new("RGB", (100, 100), (128, 128, 128))
        b = Image.new("RGB", (100, 100), (128, 128, 128))
        c = Image.new("RGB", (100, 100), (200, 200, 200))
        self.assertAlmostEqual(watch.mad(a, b), 0.0, places=1)
        self.assertGreater(watch.mad(a, c), 50.0)




if __name__ == "__main__":
    unittest.main()
