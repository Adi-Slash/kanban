# Backend Agent Guide

## Scope

- `backend/` contains the FastAPI service for the Project Management MVP.
- In Phase 2, backend serves a static hello-world page and a sample API endpoint.

## Current Structure

- `backend/app/main.py`: FastAPI app entrypoint.
  - `GET /` serves `backend/static/index.html`.
  - `GET /api/hello` returns a simple JSON payload.
- `backend/static/index.html`: static smoke page that also calls `/api/hello`.
- `backend/pyproject.toml`: backend Python project metadata/dependencies.

## Runtime

- Container runtime is defined at repository root (`Dockerfile`, `docker-compose.yml`).
- Python package management in container uses `uv`.

## Agent Guidance

- Keep backend changes minimal and phase-focused.
- Preserve root route/API behavior unless phase goals explicitly change it.
- Add backend tests alongside new backend behavior in later phases.