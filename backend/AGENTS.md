# Backend Agent Guide

## Scope

- `backend/` contains the FastAPI service for the Project Management MVP.
- Backend serves the exported frontend app at `/` and API routes under `/api`.

## Current Structure

- `backend/app/main.py`: imports and exposes app instance from factory.
- `backend/app/factory.py`: app wiring, startup DB init, and API route definitions.
- `backend/app/db.py`: SQLite schema, seed data, and DB bootstrap utilities.
- `backend/app/repository.py`: repository/service operations for board reads and mutations.
- `backend/app/schemas.py`: request/response models.
- `backend/static/`: built frontend output copied during Docker image build.
- `backend/pyproject.toml`: backend Python project metadata/dependencies.
- `backend/tests/`: pytest coverage for API, repository, and startup bootstrap.

## API Overview

- `GET /api/hello`
- `GET /api/board?username=user`
- `PATCH /api/columns/{column_id}?username=user`
- `POST /api/columns/{column_id}/cards?username=user`
- `DELETE /api/columns/{column_id}/cards/{card_id}?username=user`
- `POST /api/cards/{card_id}/move?username=user`

## Runtime

- Container runtime is defined at repository root (`Dockerfile`, `docker-compose.yml`).
- Python package management in container uses `uv`.

## Agent Guidance

- Keep backend changes minimal and phase-focused.
- Preserve `/api/*` behavior unless phase goals explicitly change it.
- Add/adjust backend tests with every backend behavior change.