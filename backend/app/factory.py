import os
from contextlib import asynccontextmanager
from pathlib import Path

from fastapi import FastAPI, HTTPException, Query, Request, Response
from fastapi.staticfiles import StaticFiles

from app.ai import AIClientError, OpenRouterClient, load_openrouter_api_key
from app.db import parse_api_id
from app.repository import KanbanRepository, NotFoundError, ValidationError
from app.schemas import (
    AIChatRequest,
    AIChatResponse,
    AISmokeResponse,
    Board,
    CreateCardRequest,
    MoveCardRequest,
    RenameColumnRequest,
)


AUTH_COOKIE_NAME = "pm_auth"
AUTH_COOKIE_VALUE = "user"
VALID_USERNAME = "user"


def _default_db_path() -> Path:
    explicit = os.getenv("DB_PATH")
    if explicit:
        explicit_path = Path(explicit).resolve()
        allowed_dir = Path(__file__).resolve().parents[1] / "data"
        try:
            explicit_path.relative_to(allowed_dir)
        except ValueError:
            raise ValueError(f"DB_PATH must be within {allowed_dir}")
        return explicit_path
    return Path(__file__).resolve().parents[1] / "data" / "pm.db"


def create_app(db_path: Path | None = None) -> FastAPI:
    static_dir = Path(__file__).resolve().parents[1] / "static"
    repo = KanbanRepository(db_path or _default_db_path())

    @asynccontextmanager
    async def lifespan(app: FastAPI):
        if not static_dir.exists():
            raise RuntimeError(f"Static directory does not exist: {static_dir}")
        app.state.repo = repo
        app.state.repo.initialize()
        try:
            api_key = load_openrouter_api_key()
            app.state.ai_client = OpenRouterClient(api_key=api_key)
            app.state.ai_client_error = None
        except AIClientError as exc:
            app.state.ai_client = None
            app.state.ai_client_error = exc
        yield

    app = FastAPI(title="Project Management MVP API", lifespan=lifespan)

    def _require_auth(request: Request, username: str | None = None) -> str:
        cookie = request.cookies.get(AUTH_COOKIE_NAME)
        if cookie != AUTH_COOKIE_VALUE:
            raise HTTPException(status_code=401, detail="Not authenticated")
        return username or VALID_USERNAME

    @app.post("/api/auth/login")
    def login(
        response: Response, username: str = Query(), password: str = Query()
    ) -> dict[str, str]:
        if username == VALID_USERNAME and password == "password":
            response.set_cookie(
                key=AUTH_COOKIE_NAME,
                value=AUTH_COOKIE_VALUE,
                httponly=True,
                samesite="lax",
                max_age=86400,
            )
            return {"message": "Login successful"}
        raise HTTPException(status_code=401, detail="Invalid credentials")

    @app.post("/api/auth/logout")
    def logout(response: Response) -> dict[str, str]:
        response.delete_cookie(key=AUTH_COOKIE_NAME, samesite="lax")
        return {"message": "Logged out"}

    @app.get("/api/auth/status")
    def auth_status(request: Request) -> dict[str, bool]:
        cookie = request.cookies.get(AUTH_COOKIE_NAME)
        return {"authenticated": cookie == AUTH_COOKIE_VALUE}

    @app.get("/api/hello")
    def hello() -> dict[str, str]:
        return {"message": "hello from fastapi"}

    @app.get("/api/board", response_model=Board)
    def get_board(
        request: Request, username: str | None = Query(default=None)
    ) -> Board:
        auth_username = _require_auth(request, username)
        try:
            return request.app.state.repo.get_board(auth_username)
        except NotFoundError as exc:
            raise HTTPException(status_code=404, detail=str(exc)) from exc

    @app.patch("/api/columns/{column_id}", response_model=Board)
    def rename_column(
        request: Request,
        column_id: str,
        payload: RenameColumnRequest,
        username: str | None = Query(default=None),
    ) -> Board:
        auth_username = _require_auth(request, username)
        try:
            return request.app.state.repo.rename_column(
                auth_username, column_id, payload.title
            )
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
        username: str | None = Query(default=None),
    ) -> Board:
        auth_username = _require_auth(request, username)
        try:
            return request.app.state.repo.create_card(
                username=auth_username,
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
        username: str | None = Query(default=None),
    ) -> Board:
        auth_username = _require_auth(request, username)
        try:
            return request.app.state.repo.delete_card(auth_username, column_id, card_id)
        except ValueError as exc:
            raise HTTPException(status_code=422, detail=str(exc)) from exc
        except NotFoundError as exc:
            raise HTTPException(status_code=404, detail=str(exc)) from exc

    @app.post("/api/cards/{card_id}/move", response_model=Board)
    def move_card(
        request: Request,
        card_id: str,
        payload: MoveCardRequest,
        username: str | None = Query(default=None),
    ) -> Board:
        auth_username = _require_auth(request, username)
        try:
            parse_api_id(payload.targetColumnId, "col")
            if payload.beforeCardId is not None:
                parse_api_id(payload.beforeCardId, "card")
            return request.app.state.repo.move_card(
                username=auth_username,
                card_api_id=card_id,
                target_column_api_id=payload.targetColumnId,
                before_card_api_id=payload.beforeCardId,
            )
        except ValueError as exc:
            raise HTTPException(status_code=422, detail=str(exc)) from exc
        except NotFoundError as exc:
            raise HTTPException(status_code=404, detail=str(exc)) from exc

    @app.post("/api/ai/smoke", response_model=AISmokeResponse)
    def ai_smoke_check(request: Request) -> AISmokeResponse:
        _require_auth(request)
        startup_error = request.app.state.ai_client_error
        if startup_error is not None:
            raise HTTPException(status_code=503, detail=str(startup_error))

        try:
            return request.app.state.ai_client.smoke_check()
        except AIClientError as exc:
            if exc.kind == "timeout":
                raise HTTPException(status_code=504, detail=str(exc)) from exc
            if exc.kind == "config_error":
                raise HTTPException(status_code=503, detail=str(exc)) from exc
            raise HTTPException(status_code=502, detail=str(exc)) from exc

    @app.post("/api/ai/chat", response_model=AIChatResponse)
    def ai_chat(
        request: Request,
        payload: AIChatRequest,
        username: str | None = Query(default=None),
    ) -> AIChatResponse:
        auth_username = _require_auth(request, username)
        startup_error = request.app.state.ai_client_error
        if startup_error is not None:
            raise HTTPException(status_code=503, detail=str(startup_error))

        try:
            current_board = request.app.state.repo.get_board(auth_username)
            assistant_message, operations = request.app.state.ai_client.build_plan(
                board_snapshot=current_board.model_dump(),
                user_message=payload.message,
                conversation_history=[
                    {"role": message.role, "content": message.content}
                    for message in payload.history
                ],
            )
            updated_board = request.app.state.repo.apply_ai_operations(
                auth_username, operations
            )
            return AIChatResponse(
                assistantMessage=assistant_message,
                operations=operations,
                board=updated_board,
            )
        except (NotFoundError, ValidationError, ValueError) as exc:
            raise HTTPException(status_code=400, detail=str(exc)) from exc
        except AIClientError as exc:
            if exc.kind == "timeout":
                raise HTTPException(status_code=504, detail=str(exc)) from exc
            if exc.kind == "config_error":
                raise HTTPException(status_code=503, detail=str(exc)) from exc
            raise HTTPException(status_code=502, detail=str(exc)) from exc

    @app.get("/health")
    def health_check() -> dict[str, str]:
        return {"status": "ok"}

    app.mount("/", StaticFiles(directory=static_dir, html=True), name="frontend")
    return app
