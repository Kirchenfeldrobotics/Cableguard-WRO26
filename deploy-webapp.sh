#!/usr/bin/env bash
set -euo pipefail

REPO="/development/Cableguard-WRO26"
APP="$REPO/webapp"
BRANCH="main"
SERVICE="cableguard-webapp"
LOCK="/tmp/cableguard-webapp-deploy.lock"

log() { echo "[$(date -Is)] $*"; }

exec 9>"$LOCK"
if ! flock -n 9; then
    log "deploy already running, skipping"
    exit 0
fi

log "fetching"
cd "$REPO"
git fetch origin "$BRANCH"

BEFORE=$(git rev-parse HEAD)
git reset --hard "origin/$BRANCH"
AFTER=$(git rev-parse HEAD)

if [ "$BEFORE" = "$AFTER" ]; then
    log "already at $AFTER, nothing to do"
    exit 0
fi

# Only rebuild if the webapp actually changed
if git diff --quiet "$BEFORE" "$AFTER" -- webapp/; then
    log "no changes under webapp/, skipping build"
    exit 0
fi

log "deploying $BEFORE -> $AFTER"
cd "$APP"

log "installing dependencies"
npm ci

log "building"
npm run build

log "restarting service"
sudo systemctl restart "$SERVICE"

sleep 3
if systemctl is-active --quiet "$SERVICE"; then
    log "deploy ok"
else
    log "service failed to start"
    exit 1
fi