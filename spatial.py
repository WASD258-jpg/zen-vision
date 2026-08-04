#!/usr/bin/env python3
"""可选空间检测：cv2.dnn + YOLOv5s (ONNX)，输出物体 bbox 像素坐标。
本地推理、零 API 额度。模型: models/yolov5s.onnx（~14MB）。
用法（配合 vision.py --spatial）：描述 + 每个物体的像素坐标，
纯文本模型可据此推算空间关系和精确位置。
"""
from pathlib import Path

BASE = Path(__file__).resolve().parent
MODEL = BASE / "models" / "yolov5s.onnx"
CONF_THRESH = 0.3
NMS_THRESH = 0.45
INPUT_SIZE = 640

COCO_NAMES = [
    "person", "bicycle", "car", "motorcycle", "airplane", "bus", "train", "truck", "boat",
    "traffic light", "fire hydrant", "stop sign", "parking meter", "bench", "bird", "cat",
    "dog", "horse", "sheep", "cow", "elephant", "bear", "zebra", "giraffe", "backpack",
    "umbrella", "handbag", "tie", "suitcase", "frisbee", "skis", "snowboard", "sports ball",
    "kite", "baseball bat", "baseball glove", "skateboard", "surfboard", "tennis racket",
    "bottle", "wine glass", "cup", "fork", "knife", "spoon", "bowl", "banana", "apple",
    "sandwich", "orange", "broccoli", "carrot", "hot dog", "pizza", "donut", "cake", "chair",
    "couch", "potted plant", "bed", "dining table", "toilet", "tv", "laptop", "mouse",
    "remote", "keyboard", "cell phone", "microwave", "oven", "toaster", "sink", "refrigerator",
    "book", "clock", "vase", "scissors", "teddy bear", "hair drier", "toothbrush",
]

_net = None


class ModelMissingError(FileNotFoundError):
    pass


def _load():
    global _net
    if _net is not None:
        return _net
    if not MODEL.exists():
        raise ModelMissingError(f"检测模型缺失：需要 models/yolov5s.onnx（~14MB）")
    import cv2
    _net = cv2.dnn.readNetFromONNX(str(MODEL))
    return _net


def letterbox(img, size=INPUT_SIZE):
    """YOLOv5 风格 letterbox：等比缩放 + 居中灰边 pad，返回 (画布, scale, pad_x, pad_y)。"""
    import cv2
    import numpy as np
    h, w = img.shape[:2]
    scale = min(size / w, size / h)
    nw, nh = int(round(w * scale)), int(round(h * scale))
    resized = cv2.resize(img, (nw, nh), interpolation=cv2.INTER_LINEAR)
    canvas = np.full((size, size, 3), 114, dtype=np.uint8)
    pad_x, pad_y = (size - nw) // 2, (size - nh) // 2
    canvas[pad_y:pad_y + nh, pad_x:pad_x + nw] = resized
    return canvas, scale, pad_x, pad_y


def detect(image):
    """image: PIL Image -> [(label, conf, x1, y1, x2, y2), ...]（原图像素坐标）"""
    import cv2
    import numpy as np
    net = _load()
    img = np.array(image.convert("RGB"))
    h, w = img.shape[:2]
    canvas, scale, pad_x, pad_y = letterbox(img)
    blob = cv2.dnn.blobFromImage(canvas, 1 / 255.0, (INPUT_SIZE, INPUT_SIZE),
                                 swapRB=False, crop=False)
    net.setInput(blob)
    outs = net.forward()  # (1, 25200, 85)
    pred = outs[0] if outs.ndim == 3 else outs
    obj_conf = pred[:, 4]
    cls_scores = pred[:, 5:]
    class_ids = cls_scores.argmax(axis=1)
    class_conf = cls_scores.max(axis=1)
    scores = obj_conf * class_conf
    mask = scores > CONF_THRESH
    if not mask.any():
        return []
    xywh = pred[mask][:, :4]
    ids = class_ids[mask]
    scs = scores[mask]

    def to_img_x(v):
        return (v - pad_x) / scale

    def to_img_y(v):
        return (v - pad_y) / scale

    boxes = []
    for cx, cy, bw, bh in xywh:
        x1 = int(max(0, min(w, to_img_x(cx - bw / 2))))
        y1 = int(max(0, min(h, to_img_y(cy - bh / 2))))
        x2 = int(max(0, min(w, to_img_x(cx + bw / 2))))
        y2 = int(max(0, min(h, to_img_y(cy + bh / 2))))
        boxes.append([x1, y1, x2 - x1, y2 - y1])
    idxs = cv2.dnn.NMSBoxes(boxes, scs.tolist(), CONF_THRESH, NMS_THRESH)
    result = []
    if idxs is not None and len(idxs) > 0:
        for i in np.atleast_2d(idxs).flatten():
            x, y, bw, bh = boxes[int(i)]
            result.append((COCO_NAMES[int(ids[int(i)])], round(float(scs[int(i)]), 2), x, y, x + bw, y + bh))
    return result


def format_detections(dets):
    if not dets:
        return "(未检测到物体)"
    return " | ".join(
        f"{label}({x1},{y1},{x2},{y2}) {conf}" for label, conf, x1, y1, x2, y2 in dets
    )
