#!/usr/bin/env python3
"""Merges several Roboflow YOLO exports into a single dataset in the layout the training notebook expects (`images/` and `labels/` per split plus `data.yaml`), unifying the class names of all sources into one list and remapping the class ids in every label file accordingly.
"""

import argparse
import os
import shutil
import sys
from pathlib import Path

import yaml

IMG_EXT = {'.jpg', '.jpeg', '.png', '.bmp', '.tif', '.tiff', '.webp'}
SPLITS = {'train': ('train',), 'val': ('val', 'valid'), 'test': ('test',)}


def load_names(src):
    """Class names from a Roboflow data.yaml, as a list indexed by class id."""
    cfg_file = src / 'data.yaml'
    if not cfg_file.exists():
        return []
    cfg = yaml.safe_load(cfg_file.read_text(encoding='utf-8')) or {}
    names = cfg.get('names') or []
    if isinstance(names, dict):                       # {0: 'defect', 1: 'ok'}
        names = [names[k] for k in sorted(names, key=int)]
    return list(names)


def find_split(src, split):
    """Image/label dir of one split, for both common export layouts."""
    for alias in SPLITS[split]:
        for images, labels in ((src / alias / 'images', src / alias / 'labels'),
                               (src / 'images' / alias, src / 'labels' / alias)):
            if images.is_dir():
                return images, labels
    return None, None


def place(src_file, dst_file):
    """Hardlink if possible - a copy of ~22'000 images costs several GB twice."""
    if dst_file.exists():
        dst_file.unlink()
    try:
        os.link(src_file, dst_file)
    except OSError:
        shutil.copy2(src_file, dst_file)


def write_label(src_label, dst_label, mapping):
    """Copy one label file with its class ids remapped."""
    lines = []
    for line in src_label.read_text(encoding='utf-8').splitlines():
        parts = line.split()
        if not parts:
            continue
        parts[0] = str(mapping.get(int(parts[0]), int(parts[0])))
        lines.append(' '.join(parts))
    dst_label.write_text('\n'.join(lines) + ('\n' if lines else ''), encoding='utf-8')


def main():
    ap = argparse.ArgumentParser(
        description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument('--src', nargs='+', required=True, type=Path,
                    help='Roboflow export directories to merge')
    ap.add_argument('--out', required=True, type=Path,
                    help='target directory, this is the DATA path in the notebook')
    args = ap.parse_args()

    for src in args.src:
        if not src.is_dir():
            sys.exit(f'source not found: {src}')
    if len({src.name for src in args.src}) != len(args.src):
        sys.exit('source directory names must be unique, they are used as filename prefixes')

    out = args.out
    for split in SPLITS:
        (out / 'images' / split).mkdir(parents=True, exist_ok=True)
        (out / 'labels' / split).mkdir(parents=True, exist_ok=True)

    names = []                                        # union over all sources
    counts = dict.fromkeys(SPLITS, 0)

    for src in args.src:
        src_names = load_names(src)
        if not src_names:
            print(f'{src}: no data.yaml with names, class ids are kept as they are')
        mapping = {}
        for class_id, name in enumerate(src_names):
            if name not in names:
                names.append(name)
            mapping[class_id] = names.index(name)

        prefix = f'{src.name}_'                       # keeps filenames unique across sources
        for split in SPLITS:
            images, labels = find_split(src, split)
            if images is None:
                print(f'{src}: no {split} split')
                continue
            n = 0
            for image in sorted(images.iterdir()):
                if image.suffix.lower() not in IMG_EXT:
                    continue
                place(image, out / 'images' / split / (prefix + image.name))
                label = labels / (image.stem + '.txt')
                if label.exists():
                    write_label(label, out / 'labels' / split / (prefix + label.name), mapping)
                n += 1
            counts[split] += n
            print(f'{src} {split}: {n} images')

    cfg = {
        'path': str(out.resolve()),
        'train': 'images/train',
        'val': 'images/val',
    }
    if counts['test']:
        cfg['test'] = 'images/test'
    cfg['nc'] = len(names)
    cfg['names'] = {i: name for i, name in enumerate(names)}
    (out / 'data.yaml').write_text(
        yaml.safe_dump(cfg, sort_keys=False, allow_unicode=True), encoding='utf-8')

    print()
    print(f'classes: {dict(enumerate(names))}')
    print(f'images:  ' + ', '.join(f'{s}={c}' for s, c in counts.items()))
    print(f'written: {out / "data.yaml"}')


if __name__ == '__main__':
    main()
