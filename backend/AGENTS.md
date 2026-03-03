# Backend Agent Guide

## Scope

- `backend/` contains the FastAPI service for the Project Management app.
- Backend serves the exported frontend app at `/` and API routes under `/api`.

## Current Structure

- `backend/app/main.py`: imports and exposes app instance from factory.
- `backend/app/factory.py`: app wiring, startup DB init, session management, and API route definitions.
- `backend/app/db.py`: SQLite schema (v2), seed data, password hashing, and DB bootstrap utilities.
- `backend/app/repository.py`: repository/service operations for user management, board CRUD, card CRUD, labels, and AI operations.
- `backend/app/schemas.py`: request/response Pydantic models.
- `backend/app/ai.py`: OpenRouter client for AI chat.
- `backend/static/`: built frontend output copied during Docker image build.
- `backend/pyproject.toml`: backend Python project metadata/dependencies.
- `backend/tests/`: pytest coverage for API, repository, auth, labels, and startup bootstrap.

## API Overview

Auth:
- `POST /api/auth/register` - register user (JSON body)
- `POST /api/auth/login` - login (JSON body)
- `POST /api/auth/logout`
- `GET /api/auth/status`
- `GET /api/auth/profile`
- `PATCH /api/auth/profile`

Boards:
- `GET /api/boards`
- `POST /api/boards`
- `GET /api/boards/{board_id}`
- `PATCH /api/boards/{board_id}`
- `DELETE /api/boards/{board_id}`

Board operations (all require auth, board must belong to user):
- `PATCH /api/boards/{board_id}/columns/{column_id}`
- `POST /api/boards/{board_id}/columns/{column_id}/cards`
- `PATCH /api/boards/{board_id}/cards/{card_id}`
- `DELETE /api/boards/{board_id}/columns/{column_id}/cards/{card_id}`
- `POST /api/boards/{board_id}/cards/{card_id}/move`
- `PUT /api/boards/{board_id}/cards/{card_id}/labels`
- `POST /api/boards/{board_id}/labels`
- `PATCH /api/boards/{board_id}/labels/{label_id}`
- `DELETE /api/boards/{board_id}/labels/{label_id}`
- `POST /api/boards/{board_id}/ai/chat`

## Runtime

- Container runtime is defined at repository root (`Dockerfile`, `docker-compose.yml`).
- Python package management in container uses `uv`.

## Agent Guidance

- Keep backend changes minimal and phase-focused.
- Preserve `/api/*` behavior unless phase goals explicitly change it.
- Add/adjust backend tests with every backend behavior change.
