import os
from contextlib import asynccontextmanager
from pathlib import Path

from fastapi import FastAPI, HTTPException, Query, Request
from fastapi.staticfiles import StaticFiles

from app.db import parse_api_id
from app.repository import KanbanRepository, NotFoundError, ValidationError
from app.schemas import Board, CreateCardRequest, MoveCardRequest, RenameColumnRequest


def _default_db_path() -> Path:
    explicit = os.getenv("DB_PATH")
    if explicit:
        return Path(explicit)
    return Path(__file__).resolve().parents[1] / "data" / "pm.db"


def create_app(db_path: Path | None = None) -> FastAPI:
    static_dir = Path(__file__).resolve().parents[1] / "static"
    repo = KanbanRepository(db_path or _default_db_path())

    @asynccontextmanager
    async def lifespan(app: FastAPI):
        app.state.repo = repo
        app.state.repo.initialize()
        yield

    app = FastAPI(title="Project Management MVP API", lifespan=lifespan)

    @app.get("/api/hello")
    def hello() -> dict[str, str]:
        return {"message": "hello from fastapi"}

    @app.get("/api/board", response_model=Board)
    def get_board(request: Request, username: str = Query(default="user")) -> Board:
        try:
            return request.app.state.repo.get_board(username)
        except NotFoundError as exc:
            raise HTTPException(status_code=404, detail=str(exc)) from exc

    @app.patch("/api/columns/{column_id}", response_model=Board)
    def rename_column(
        request: Request,
        column_id: str,
        payload: RenameColumnRequest,
        username: str = Query(default="user"),
    ) -> Board:
        try:
            return request.app.state.repo.rename_column(username, column_id, payload.title)
        except ValueError as exc:
            raise HTTPException(status_code=422, detail=str(exc)) from exc
        except ValidationError as exc:
            raise HTTPException(status_code=400, detail=str(exc)) from exc
        except NotFoundError as exc:
            raise HTTPException(status_code=404, detail=str(exc)) from exc

    @app.post("/api/columns/{column_id}/cards", response_model=Board)
    def add_card(
        request: Request,
        column_id: str,
        payload: CreateCardRequest,
        username: str = Query(default="user"),
    ) -> Board:
        try:
            return request.app.state.repo.create_card(
                username=username,
                column_api_id=column_id,
                title=payload.title,
                details=payload.details,
            )
        except ValueError as exc:
            raise HTTPException(status_code=422, detail=str(exc)) from exc
        except ValidationError as exc:
            raise HTTPException(status_code=400, detail=str(exc)) from exc
        except NotFoundError as exc:
            raise HTTPException(status_code=404, detail=str(exc)) from exc

    @app.delete("/api/columns/{column_id}/cards/{card_id}", response_model=Board)
    def remove_card(
        request: Request,
        column_id: str,
        card_id: str,
        username: str = Query(default="user"),
    ) -> Board:
        try:
            return request.app.state.repo.delete_card(username, column_id, card_id)
        except ValueError as exc:
            raise HTTPException(status_code=422, detail=str(exc)) from exc
        except NotFoundError as exc:
            raise HTTPException(status_code=404, detail=str(exc)) from exc

    @app.post("/api/cards/{card_id}/move", response_model=Board)
    def move_card(
        request: Request,
        card_id: str,
        payload: MoveCardRequest,
        username: str = Query(default="user"),
    ) -> Board:
        try:
            # Validate format here for clear 422 on malformed target ids.
            parse_api_id(payload.targetColumnId, "col")
            if payload.beforeCardId is not None:
                parse_api_id(payload.beforeCardId, "card")
            return request.app.state.repo.move_card(
                username=username,
                card_api_id=card_id,
                target_column_api_id=payload.targetColumnId,
                before_card_api_id=payload.beforeCardId,
            )
        except ValueError as exc:
            raise HTTPException(status_code=422, detail=str(exc)) from exc
        except NotFoundError as exc:
            raise HTTPException(status_code=404, detail=str(exc)) from exc

    app.mount("/", StaticFiles(directory=static_dir, html=True), name="frontend")
    return app
