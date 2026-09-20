import argparse
import hashlib
import shutil
import sys
from datetime import date
from pathlib import Path

import yaml
from ultralytics import YOLO

HERE = Path(__file__).resolve().parent


def train_imgsz(model):
    """The imgsz the checkpoint was trained with, as a single int."""
    imgsz = ((model.ckpt or {}).get('train_args') or {}).get('imgsz')
    if isinstance(imgsz, (list, tuple)):              # some runs store [h, w]
        imgsz = max(imgsz)
    return int(imgsz) if imgsz else None


def export(weights, fmt, imgsz):
    try:
        return Path(YOLO(weights).export(format=fmt, imgsz=imgsz))   # fresh load, export mutates the model
    except Exception as exc:
        print(f'{fmt} export failed: {exc}')
        return None


def place(src, dst):
    if dst.is_dir():
        shutil.rmtree(dst)
    elif dst.exists():
        dst.unlink()
    if src.is_dir():
        shutil.copytree(src, dst)
    else:
        shutil.copy2(src, dst)
    return dst.name


def main():
    ap = argparse.ArgumentParser(
        description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument('--weights', type=Path, default=HERE / 'runs' / 'wirerope' / 'weights' / 'best.pt',
                    help='trained checkpoint, by default the best.pt of the notebook run')
    ap.add_argument('--out', type=Path, default=HERE.parent / 'robot' / 'models',
                    help='target directory, this is what gets copied to the Pi')
    args = ap.parse_args()

    if not args.weights.is_file():
        sys.exit(f'weights not found: {args.weights}')

    model = YOLO(args.weights)
    imgsz = train_imgsz(model)
    if imgsz is None:
        sys.exit(f'{args.weights} stores no training imgsz, export would not match training')
    names = {int(i): name for i, name in model.names.items()}
    print(f'imgsz={imgsz} (from training), classes: {names}')

    args.out.mkdir(parents=True, exist_ok=True)
    exports = {}
    ncnn = export(args.weights, 'ncnn', imgsz)        # fastest on the Pi's ARM CPU
    if ncnn:
        exports['ncnn'] = place(ncnn, args.out / ncnn.name)
    onnx = export(args.weights, 'onnx', imgsz)        # fallback
    if onnx:
        exports['onnx'] = place(onnx, args.out / onnx.name)
    if not exports:
        sys.exit('both exports failed, nothing written')

    today = date.today().isoformat()
    run = args.weights.parent.parent.name             # runs/<run>/weights/best.pt
    digest = hashlib.sha256(args.weights.read_bytes()).hexdigest()[:8]

    cfg = {'version': f'{run}-{today}-{digest}', 'exported': today, 'imgsz': imgsz}
    cfg.update(exports)
    cfg['names'] = names
    (args.out / 'model.yaml').write_text(
        yaml.safe_dump(cfg, sort_keys=False, allow_unicode=True), encoding='utf-8')

    print()
    print(f'version: {cfg["version"]}')
    print(f'written: {args.out}')


if __name__ == '__main__':
    main()
