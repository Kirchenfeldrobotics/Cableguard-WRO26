#!/bin/bash
set -e
 
REPO_DIR="/development/Cableguard-WRO26"
APP_DIR="$REPO_DIR/webapp"
LOG="$REPO_DIR/deploy.log"
 
exec >> "$LOG" 2>&1
echo "===== Deploy started at $(date) ====="
 
cd "$REPO_DIR"
git fetch --all
git reset --hard origin/main
 
cd "$APP_DIR"
npm ci
npm run build
pm2 reload cableguard-webapp --update-env
 
echo "===== Deploy finished at $(date) ====="