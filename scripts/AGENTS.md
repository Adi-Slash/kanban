# Scripts Agent Guide

This folder contains local lifecycle scripts for the Dockerized app.

## Scripts

- Windows:
  - `scripts/start-win.ps1`
  - `scripts/stop-win.ps1`
- macOS:
  - `scripts/start-mac.sh`
  - `scripts/stop-mac.sh`
- Linux:
  - `scripts/start-linux.sh`
  - `scripts/stop-linux.sh`

## Behavior

- Start scripts run `docker compose up --build -d`.
- Stop scripts run `docker compose down`.

Keep script behavior simple and consistent across platforms.