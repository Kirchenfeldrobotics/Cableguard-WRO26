import logging
import multiprocessing as mp
import signal
import threading
import time
from dataclasses import dataclass
from pathlib import Path

import numpy as np
import yaml

log = logging.getLogger(__name__)

# Model folder
MODEL_DIR = Path(__file__).resolve().parents[2] / "models" / "best_ncnn_model"

# Detection thresholds
CONF = 0.1

# IOU threshold for overlap merging
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
        # imported here so that only the detector process pays for torch
        from ultralytics import YOLO
        # task="detect" must be explicit
        self._model = YOLO(str(model_dir), task="detect")
        log.info("ncnn model loaded: %s, imgsz=%d, classes=%s",
                 model_dir.name, self.imgsz, list(self.names.values()))

    # thresholds the operator may move while the robot runs
    def configure(self, conf, iou):
        self.conf = conf
        self.iou  = iou

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


# Runs a Detector in its own process. ncnn keeps Python's GIL for the whole forward pass,
# which would freeze every other thread of the robot, the one feeding the drive included
def _serve(conn):
    logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(name)s: %(message)s")
    # Ctrl-C is for the robot process, this one ends when the pipe closes
    signal.signal(signal.SIGINT, signal.SIG_IGN)

    try:
        detector = Detector()
    except Exception as exc:
        conn.send((False, exc))
        return
    conn.send((True, None))

    while True:
        try:
            name, args = conn.recv()
        except EOFError:
            return
        try:
            conn.send((True, getattr(detector, name)(*args)))
        except Exception as exc:
            conn.send((False, exc))

# stands in for a Detector, each call blocks until the detector process answers
class DetectorProcess:

    # starts the process and waits until the model is loaded
    def __init__(self):
        # spawn, not fork: a forked child would inherit the robot's GPIO and PIO handles
        ctx = mp.get_context("spawn")
        self._conn, child = ctx.Pipe()
        self._proc = ctx.Process(target=_serve, args=(child,), name="detector", daemon=True)
        self._proc.start()
        child.close()
        self._lock = threading.Lock()
        self._answer()

    def _answer(self):
        ok, value = self._conn.recv()
        if not ok:
            raise value
        return value

    def _call(self, name, *args):
        with self._lock:
            self._conn.send((name, args))
            return self._answer()

    def detect(self, frame) -> list[Detection]:
        return self._call("detect", frame)

    def warmup(self):
        self._call("warmup")

    def configure(self, conf, iou):
        self._call("configure", conf, iou)
