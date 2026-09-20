set -euo pipefail

REPO_ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
MODEL="$REPO_ROOT/robot/models/best_ncnn_model"
TARGET="${1:-${CABLEGUARD_PI:-}}"
REMOTE_DIR="${CABLEGUARD_PI_DIR:-Cableguard-WRO26/robot/models}"

if [ -z "$TARGET" ]; then
    echo "usage: $0 user@host   (or set CABLEGUARD_PI)" >&2
    exit 1
fi
if [ ! -d "$MODEL" ]; then
    echo "no model at $MODEL" >&2
    echo "run: cd wirerope-training && python export_for_robot.py --weights weights/best.pt" >&2
    exit 1
fi

echo "==> $TARGET:$REMOTE_DIR"
ssh "$TARGET" "mkdir -p '$REMOTE_DIR'"

if command -v rsync >/dev/null 2>&1; then
    rsync -av --delete "$MODEL" "$TARGET:$REMOTE_DIR/"
else
    scp -r "$MODEL" "$TARGET:$REMOTE_DIR/"
fi

# the version file the exporter writes next to it, handy for logging which
# model a run actually used
if [ -f "$REPO_ROOT/robot/models/model.yaml" ]; then
    scp "$REPO_ROOT/robot/models/model.yaml" "$TARGET:$REMOTE_DIR/"
fi

echo "==> done"
