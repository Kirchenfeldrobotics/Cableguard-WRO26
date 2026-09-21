import logging
import time
from dataclasses import dataclass
from pathlib import Path

import numpy as np
import yaml
from ultralytics import YOLO

log = logging.getLogger(__name__)

# Model folder
MODEL_DIR = Path(__file__).resolve().parents[2] / "models" / "best_ncnn_model"

# Detection thresholds
CONF = 0.5

# IOU threshold for non-max suppression
IOU = 0.5




@dataclass(frozen=True)
class Detection:
    label: str                                  # the class name
    confidence: float                           # model confidence => 0.0-1.0
    box: tuple[float, float, float, float]      # x1, y1, x2, y2

    @property
    def center(self):
        x1, y1, x2, y2 = self.box
        return (x1 + x2) / 2.0, (y1 + y2) / 2.0

class Detector:

    # loads the network once at startup
    def __init__(self, model_dir: Path = MODEL_DIR, conf: float = CONF, iou: float = IOU):
        if not (model_dir / "model.ncnn.param").is_file():
            raise FileNotFoundError(
                f"no ncnn model in {model_dir}, run wirerope-training/export_for_robot.py and copy the folder over")
        if not model_dir.name.endswith("_ncnn_model"):  # ultralytics picks the backend from the folder name
            raise ValueError(f"{model_dir.name} must end in _ncnn_model, ultralytics reads the backend off the name")
        meta = yaml.safe_load((model_dir / "metadata.yaml").read_text(encoding="utf-8"))
        # input resolution
        imgsz = meta["imgsz"]
        self.imgsz = max(imgsz) if isinstance(imgsz, (list, tuple)) else int(imgsz)   # ncnn export is fixed size
        # class index => class name, int() because yaml may give the keys as strings
        self.names = {int(i): name for i, name in meta["names"].items()}
        self.conf = conf
        self.iou = iou
        # task="detect" must be explicit
        self._model = YOLO(str(model_dir), task="detect")
        log.info("ncnn model loaded: %s, imgsz=%d, classes=%s",
                 model_dir.name, self.imgsz, list(self.names.values()))

    def _infer(self, frame):
        return self._model.predict(
            frame, imgsz=self.imgsz, conf=self.conf, iou=self.iou, verbose=False)[0]

    def detect(self, frame) -> list[Detection]:
        return [
            Detection(
                label=self.names.get(int(box.cls), "unknown"),
                confidence=float(box.conf),
                box=tuple(float(v) for v in box.xyxy[0]),
            )
            for box in self._infer(frame).boxes
        ]
    
    # warmup the model by running a dummy inference
    def warmup(self):
        blank = np.zeros((self.imgsz, self.imgsz, 3), dtype=np.uint8)
        started = time.monotonic()
        self.detect(blank)
        log.info("warmup done in %.0f ms", (time.monotonic() - started) * 1000.0)
