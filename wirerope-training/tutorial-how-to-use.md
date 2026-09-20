## Datasets

- https://universe.roboflow.com/wirerope-qfgck/wire-rope-defect-f4qyg
- https://universe.roboflow.com/yuan-9voxc/wire-rope-defect-review

Use Fork Dataset

## Setup

```bash
pip install -r requirements.txt
cp .env.example .env      # then put your Roboflow API key into it
```

Key into .env

## Run

1. Open `yolo26_wirerope_training.ipynb` and run the two download cells, they
   write to `datasets/A` and `datasets/B`.
2. Merge both exports into one dataset:
   ```bash
   python prepare_wirerope.py --src datasets/A datasets/B --out datasets/wirerope_merged
   ```
   The `--out` path is the `DATA` value in the notebook.
3. Run the rest of the notebook: training, validation, ONNX export, plots.

`datasets/`, `runs/`, `*.pt` and `*.onnx` are gitignored. The images are
several GB and GitHub blocks files over 100 MB.

Before pushing: `jupyter nbconvert --clear-output --inplace *.ipynb`, otherwise
the plot images end up base64-encoded in the diff.

## Export for the robot

```bash
python export_for_robot.py --weights weights/best.pt
```

Writes `robot/models/best_ncnn_model/` (param + bin + metadata.yaml), `best.onnx`
as fallback and `model.yaml` with version, imgsz and class names. The ncnn
folder is the only thing the robot needs, `robot/src/vision/detector.py` loads
it from there.

Keep `weights/best.pt`, it is the only thing that can be re-exported from.
`last.pt` is just the final epoch, needed only to resume an interrupted run.

## Deploy to the Pi

`robot/models/` is gitignored, so the weights do not travel with `git pull`.
The code goes over git, the model goes over ssh:

```bash
./scripts/deploy-model.sh pi@cableguard.local
```

Only needed after a new export, not after every code change.

## Testing on a laptop

```bash
python -m venv .venv                      # in the repo root
.venv/Scripts/python.exe -m pip install ultralytics ncnn pyyaml
```

```bash
.venv/Scripts/python.exe robot/src/vision/detector.py              # load + warmup only
.venv/Scripts/python.exe robot/src/vision/detector.py rope.jpg     # one or more images
.venv/Scripts/python.exe robot/src/vision/detector.py cam          # live webcam preview
```

The same ncnn folder runs on the laptop, no separate build needed.
