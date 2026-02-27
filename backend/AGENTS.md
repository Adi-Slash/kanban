# Backend Agent Guide

## Scope

- `backend/` contains the FastAPI service for the Project Management MVP.
- Backend serves the exported frontend app at `/` and API routes under `/api`.

## Current Structure

- `backend/app/main.py`: FastAPI app entrypoint.
  - Serves static frontend files from `backend/static` at `/`.
  - `GET /api/hello` returns a simple JSON payload.
- `backend/static/`: built frontend output copied during Docker image build.
- `backend/pyproject.toml`: backend Python project metadata/dependencies.

## Runtime

- Container runtime is defined at repository root (`Dockerfile`, `docker-compose.yml`).
- Python package management in container uses `uv`.

## Agent Guidance

- Keep backend changes minimal and phase-focused.
- Preserve root route/API behavior unless phase goals explicitly change it.
- Add backend tests alongside new backend behavior in later phases.