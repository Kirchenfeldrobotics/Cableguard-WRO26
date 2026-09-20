import logging
import time
from dataclasses import dataclass
from pathlib import Path

import numpy as np
import yaml
from ultralytics import YOLO

log = logging.getLogger(__name__)

MODEL_DIR = Path(__file__).resolve().parents[2] / "models" / "best_ncnn_model"

CONF = 0.35
IOU = 0.5

@dataclass(frozen=True)
class Detection:
    label: str
    confidence: float
    box: tuple[float, float, float, float]      # x1, y1, x2, y2

    @property
    def center(self):
        x1, y1, x2, y2 = self.box
        return (x1 + x2) / 2.0, (y1 + y2) / 2.0

class Detector:
    def __init__(self, model_dir: Path = MODEL_DIR, conf: float = CONF, iou: float = IOU):
        if not (model_dir / "model.ncnn.param").is_file():
            raise FileNotFoundError(
                f"no ncnn model in {model_dir}, run wirerope-training/export_for_robot.py and copy the folder over")
        if not model_dir.name.endswith("_ncnn_model"):
            raise ValueError(f"{model_dir.name} must end in _ncnn_model, ultralytics reads the backend off the name")

        meta = yaml.safe_load((model_dir / "metadata.yaml").read_text(encoding="utf-8"))
        imgsz = meta["imgsz"]
        self.imgsz = max(imgsz) if isinstance(imgsz, (list, tuple)) else int(imgsz)   # ncnn export is fixed size
        self.names = {int(i): name for i, name in meta["names"].items()}
        self.conf = conf
        self.iou = iou

        self._model = YOLO(str(model_dir), task="detect")
        log.info("ncnn model loaded: %s, imgsz=%d, classes=%s",
                 model_dir.name, self.imgsz, list(self.names.values()))

    # raw ultralytics result, kept for the annotated preview in the self test
    def _infer(self, frame):
        return self._model.predict(
            frame, imgsz=self.imgsz, conf=self.conf, iou=self.iou, verbose=False)[0]

    # one frame in, boxes out. frames come from picamera2 as RGB888, which is
    # byte-order BGR, the same layout ultralytics expects from an ndarray
    def detect(self, frame) -> list[Detection]:
        return [
            Detection(
                label=self.names.get(int(box.cls), "unknown"),
                confidence=float(box.conf),
                box=tuple(float(v) for v in box.xyxy[0]),
            )
            for box in self._infer(frame).boxes
        ]

    # the first inference allocates the whole net, do it before the run starts
    def warmup(self):
        blank = np.zeros((self.imgsz, self.imgsz, 3), dtype=np.uint8)
        started = time.monotonic()
        self.detect(blank)
        log.info("warmup done in %.0f ms", (time.monotonic() - started) * 1000.0)

def _print(source, found, millis):
    print(f"{source}: {len(found)} detections in {millis:.0f} ms")
    for det in found:
        x1, y1, x2, y2 = det.box
        print(f"  {det.label:<18} {det.confidence:.2f}  [{x1:.0f}, {y1:.0f}, {x2:.0f}, {y2:.0f}]")

# laptop preview, hold a rope photo in front of the webcam, q closes the window
def _webcam(detector):
    import cv2

    cam = cv2.VideoCapture(0)
    if not cam.isOpened():
        raise RuntimeError("no webcam found")
    try:
        while True:
            ok, frame = cam.read()
            if not ok:
                break
            started = time.monotonic()
            result = detector._infer(frame)
            millis = (time.monotonic() - started) * 1000.0
            cv2.imshow("cableguard", result.plot())
            if cv2.waitKey(1) & 0xFF == ord("q"):
                break
            print(f"\r{len(result.boxes)} detections, {millis:.0f} ms/frame", end="", flush=True)
    finally:
        cam.release()
        cv2.destroyAllWindows()

# python detector.py             load the net and warm up, checks the export
# python detector.py rope.jpg    one or more images
# python detector.py cam         live preview from the laptop webcam
if __name__ == "__main__":
    import sys

    logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(name)s: %(message)s")

    detector = Detector()
    detector.warmup()

    if sys.argv[1:] == ["cam"]:
        _webcam(detector)
    else:
        for source in sys.argv[1:]:
            started = time.monotonic()
            found = detector.detect(source)
            _print(source, found, (time.monotonic() - started) * 1000.0)
