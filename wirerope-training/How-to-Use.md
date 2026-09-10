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
