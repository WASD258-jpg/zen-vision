#!/usr/bin/env python3
"""实时视力：监控屏幕 / 视频 / 摄像头，画面变化时自动描述。

用法:
  python watch.py screen [--interval 1] [--threshold 8] [--cooldown 8] [-q 提示] [--once]
  python watch.py video 视频.mp4 [--every 1] [--threshold 8] [-q 提示]
  python watch.py camera [--threshold 8] [-q 提示]

原理: 本地检测画面变化(像素差 MAD，零 API 调用)，有变化才调视觉模型描述。
依赖: pip install pillow numpy requests（视频/摄像头另需 opencv-python）
"""
import argparse
import base64
import io
import sys
import time

from PIL import Image, ImageChops, ImageGrab

import vision

DEFAULT_PROMPT = "描述这张画面上的内容：可见的文字、界面元素、明显的事件或变化。"


def mad(a, b, size=64):
    """纯 PIL 计算平均绝对差（无 numpy），0-255 范围。"""
    a = a.convert("L").resize((size, size), Image.LANCZOS)
    b = b.convert("L").resize((size, size), Image.LANCZOS)
    hist = ImageChops.difference(a, b).histogram()
    total = sum(v * i for i, v in enumerate(hist))
    return total / (size * size)


def pil_to_data_url(img):
    buf = io.BytesIO()
    img.save(buf, format="PNG")
    return "data:image/png;base64," + base64.b64encode(buf.getvalue()).decode()


def analyze(img, prompt):
    return vision.ask([pil_to_data_url(img)], prompt)


def report(desc, count, once):
    print(f"\n[{time.strftime('%H:%M:%S')}] 画面变化 #{count}:")
    print(desc)
    return once


def watch_loop(get_frame, args):
    baseline = None
    pending = 0
    trigger_count = 0
    last_trigger = 0.0
    print("监控中（Ctrl+C 停止）...")
    for time_str, desc in collect_changes(
        get_frame,
        duration=None,
        interval=args.interval,
        threshold=args.threshold,
        cooldown=args.cooldown,
        stable=args.stable,
        query=args.query,
        on_change=lambda t, d, n: report(d, n, args.once),
    ):
        pass


def collect_changes(get_frame, duration=None, interval=1.0, threshold=8.0,
                    cooldown=8.0, stable=2, query=None, on_change=None):
    """监控直到 duration 秒（None=无限），返回 [(时间, 描述), ...]。
    get_frame: 取一帧 PIL Image 的可调用对象（返回 None 表示结束/失败）。
    on_change: 可选回调 (时间, 描述, 序号)，用于实时打印。
    """
    results = []
    baseline = None
    pending = 0
    trigger_count = 0
    last_trigger = 0.0
    start = time.time()
    while duration is None or time.time() - start < duration:
        try:
            frame = get_frame()
        except Exception as e:
            print(f"取帧失败: {e}")
            if interval:
                time.sleep(interval)
            continue
        if frame is None:
            break
        if baseline is None:
            baseline = frame
        else:
            diff = mad(frame, baseline)
            now = time.time()
            if diff >= threshold:
                pending += 1
                if pending >= stable and now - last_trigger >= cooldown:
                    try:
                        desc = analyze(frame, query or DEFAULT_PROMPT)
                    except SystemExit as e:
                        desc = f"(分析失败: {e})"
                    time_str = time.strftime("%H:%M:%S")
                    results.append((time_str, desc))
                    trigger_count += 1
                    if on_change:
                        if on_change(time_str, desc, trigger_count):
                            break
                    baseline = frame
                    last_trigger = now
                    pending = 0
            else:
                pending = 0
        if interval:
            time.sleep(interval)
    return results


def cmd_screen(args):
    def grab():
        return ImageGrab.grab()
    watch_loop(grab, args)


def cmd_video(args):
    try:
        import cv2
    except ImportError:
        sys.exit("视频模式需要 opencv-python：pip install opencv-python")
    cap = cv2.VideoCapture(args.input)
    if not cap.isOpened():
        sys.exit(f"无法打开视频: {args.input}")
    fps = cap.get(cv2.CAP_PROP_FPS) or 30
    total = int(cap.get(cv2.CAP_PROP_FRAME_COUNT))
    step = max(1, int(round(fps * args.every)))
    print(f"视频: {fps:.0f}fps, {total} 帧, 每 {args.every}s 检 1 帧")
    changes = 0

    def grab():
        nonlocal changes
        frame = None
        pos = int(cap.get(cv2.CAP_PROP_POS_FRAMES))
        for _ in range(step):
            ret, f = cap.read()
            if not ret:
                return None
            frame = f
        changes += 1
        return Image.fromarray(frame[:, :, ::-1])  # BGR -> RGB

    try:
        watch_loop(grab, args)
    except KeyboardInterrupt:
        pass
    finally:
        cap.release()
    print(f"\n视频分析结束：检查 {changes} 帧")


def cmd_camera(args):
    try:
        import cv2
    except ImportError:
        sys.exit("摄像头模式需要 opencv-python：pip install opencv-python")
    cap = cv2.VideoCapture(0)
    if not cap.isOpened():
        sys.exit("无法打开摄像头（可能需要 opencv-python 完整版）")

    def grab():
        ret, frame = cap.read()
        if not ret:
            return None
        return Image.fromarray(frame[:, :, ::-1])

    try:
        watch_loop(grab, args)
    except KeyboardInterrupt:
        pass
    finally:
        cap.release()


def main():
    ap = argparse.ArgumentParser(description="实时视力：变化时自动描述画面")
    sub = ap.add_subparsers(dest="mode", required=True)
    for name, help_txt in (("screen", "监控屏幕"), ("video", "分析视频"), ("camera", "监控摄像头")):
        p = sub.add_parser(name, help=help_txt)
        if name == "video":
            p.add_argument("input", help="视频文件路径")
            p.add_argument("--every", type=float, default=1.0, help="检测间隔(秒)，默认 1")
        p.add_argument("--interval", type=float, default=1.0, help="取帧间隔(秒)，默认 1")
        p.add_argument("--threshold", type=float, default=8.0, help="变化判定阈值(0-255)，默认 8")
        p.add_argument("--cooldown", type=float, default=8.0, help="触发后冷却(秒)，默认 8")
        p.add_argument("--stable", type=int, default=2, help="连续几帧超阈值才算变化，默认 2")
        p.add_argument("-q", "--query", help="自定义描述提示词")
        p.add_argument("--once", action="store_true", help="触发一次后退出")
    args = ap.parse_args()
    vision.load_env()
    {
        "screen": cmd_screen,
        "video": cmd_video,
        "camera": cmd_camera,
    }[args.mode](args)


if __name__ == "__main__":
    main()
