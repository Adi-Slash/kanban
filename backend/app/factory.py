import os
import secrets
from contextlib import asynccontextmanager
from dataclasses import dataclass
from pathlib import Path

from fastapi import FastAPI, HTTPException, Request, Response
from fastapi.staticfiles import StaticFiles

from app.ai import AIClientError, OpenRouterClient, load_openrouter_api_key
from app.db import parse_api_id
from app.repository import (
    ConflictError,
    KanbanRepository,
    NotFoundError,
    ValidationError,
)
from app.schemas import (
    AIChatRequest,
    AIChatResponse,
    AISmokeResponse,
    Board,
    BoardSummary,
    CreateBoardRequest,
    CreateCardRequest,
    CreateLabelRequest,
    Label,
    LoginRequest,
    MoveCardRequest,
    ProfileResponse,
    RegisterRequest,
    RenameColumnRequest,
    SetCardLabelsRequest,
    UpdateBoardRequest,
    UpdateCardRequest,
    UpdateLabelRequest,
    UpdateProfileRequest,
)

AUTH_COOKIE_NAME = "pm_session"


@dataclass
class AuthUser:
    user_id: int
    username: str


_sessions: dict[str, AuthUser] = {}


def _create_session(user_id: int, username: str) -> str:
    token = secrets.token_urlsafe(32)
    _sessions[token] = AuthUser(user_id=user_id, username=username)
    return token


def _get_session(token: str) -> AuthUser | None:
    return _sessions.get(token)


def _destroy_session(token: str) -> None:
    _sessions.pop(token, None)


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

    app = FastAPI(title="Project Management API", lifespan=lifespan)

    def _require_auth(request: Request) -> AuthUser:
        token = request.cookies.get(AUTH_COOKIE_NAME)
        if not token:
            raise HTTPException(status_code=401, detail="Not authenticated")
        auth = _get_session(token)
        if not auth:
            raise HTTPException(status_code=401, detail="Session expired")
        return auth

    # ---- Auth endpoints ----

    @app.post("/api/auth/register")
    def register_user(request: Request, response: Response, payload: RegisterRequest) -> dict[str, str]:
        try:
            user_id = request.app.state.repo.register_user(
                payload.username, payload.password, payload.displayName
            )
        except ConflictError as exc:
            raise HTTPException(status_code=409, detail=str(exc)) from exc
        token = _create_session(user_id, payload.username)
        response.set_cookie(
            key=AUTH_COOKIE_NAME,
            value=token,
            httponly=True,
            samesite="lax",
            max_age=86400,
        )
        return {"message": "Registration successful"}

    @app.post("/api/auth/login")
    def login(request: Request, response: Response, payload: LoginRequest) -> dict[str, str]:
        user_id = request.app.state.repo.authenticate_user(
            payload.username, payload.password
        )
        if user_id is None:
            raise HTTPException(status_code=401, detail="Invalid credentials")
        token = _create_session(user_id, payload.username)
        response.set_cookie(
            key=AUTH_COOKIE_NAME,
            value=token,
            httponly=True,
            samesite="lax",
            max_age=86400,
        )
        return {"message": "Login successful"}

    @app.post("/api/auth/logout")
    def logout(request: Request, response: Response) -> dict[str, str]:
        token = request.cookies.get(AUTH_COOKIE_NAME)
        if token:
            _destroy_session(token)
        response.delete_cookie(key=AUTH_COOKIE_NAME, samesite="lax")
        return {"message": "Logged out"}

    @app.get("/api/auth/status")
    def auth_status(request: Request) -> dict[str, bool]:
        token = request.cookies.get(AUTH_COOKIE_NAME)
        if not token:
            return {"authenticated": False}
        auth = _get_session(token)
        return {"authenticated": auth is not None}

    @app.get("/api/auth/profile", response_model=ProfileResponse)
    def get_profile(request: Request) -> ProfileResponse:
        auth = _require_auth(request)
        try:
            data = request.app.state.repo.get_user_profile(auth.user_id)
            return ProfileResponse(**data)
        except NotFoundError as exc:
            raise HTTPException(status_code=404, detail=str(exc)) from exc

    @app.patch("/api/auth/profile", response_model=ProfileResponse)
    def update_profile(
        request: Request, payload: UpdateProfileRequest
    ) -> ProfileResponse:
        auth = _require_auth(request)
        request.app.state.repo.update_user_profile(auth.user_id, payload.displayName)
        data = request.app.state.repo.get_user_profile(auth.user_id)
        return ProfileResponse(**data)

    # ---- Board CRUD ----

    @app.get("/api/boards", response_model=list[BoardSummary])
    def list_boards(request: Request) -> list[BoardSummary]:
        auth = _require_auth(request)
        return request.app.state.repo.list_boards(auth.user_id)

    @app.post("/api/boards", response_model=BoardSummary, status_code=201)
    def create_board(request: Request, payload: CreateBoardRequest) -> BoardSummary:
        auth = _require_auth(request)
        return request.app.state.repo.create_board(
            auth.user_id, payload.name, payload.description
        )

    @app.get("/api/boards/{board_id}", response_model=Board)
    def get_board(request: Request, board_id: str) -> Board:
        auth = _require_auth(request)
        try:
            return request.app.state.repo.get_board(auth.user_id, board_id)
        except (NotFoundError, ValueError) as exc:
            raise HTTPException(status_code=404, detail=str(exc)) from exc

    @app.patch("/api/boards/{board_id}", response_model=BoardSummary)
    def update_board(
        request: Request, board_id: str, payload: UpdateBoardRequest
    ) -> BoardSummary:
        auth = _require_auth(request)
        try:
            return request.app.state.repo.update_board(
                auth.user_id, board_id, payload.name, payload.description
            )
        except (NotFoundError, ValueError) as exc:
            raise HTTPException(status_code=404, detail=str(exc)) from exc
        except ValidationError as exc:
            raise HTTPException(status_code=400, detail=str(exc)) from exc

    @app.delete("/api/boards/{board_id}", status_code=204)
    def delete_board(request: Request, board_id: str) -> None:
        auth = _require_auth(request)
        try:
            request.app.state.repo.delete_board(auth.user_id, board_id)
        except (NotFoundError, ValueError) as exc:
            raise HTTPException(status_code=404, detail=str(exc)) from exc

    # ---- Column operations ----

    @app.patch("/api/boards/{board_id}/columns/{column_id}", response_model=Board)
    def rename_column(
        request: Request, board_id: str, column_id: str, payload: RenameColumnRequest
    ) -> Board:
        auth = _require_auth(request)
        try:
            return request.app.state.repo.rename_column(
                auth.user_id, board_id, column_id, payload.title
            )
        except ValueError as exc:
            raise HTTPException(status_code=422, detail=str(exc)) from exc
        except ValidationError as exc:
            raise HTTPException(status_code=400, detail=str(exc)) from exc
        except NotFoundError as exc:
            raise HTTPException(status_code=404, detail=str(exc)) from exc

    # ---- Card CRUD ----

    @app.post(
        "/api/boards/{board_id}/columns/{column_id}/cards", response_model=Board
    )
    def add_card(
        request: Request,
        board_id: str,
        column_id: str,
        payload: CreateCardRequest,
    ) -> Board:
        auth = _require_auth(request)
        try:
            return request.app.state.repo.create_card(
                user_id=auth.user_id,
                board_api_id=board_id,
                column_api_id=column_id,
                title=payload.title,
                details=payload.details,
                priority=payload.priority,
                due_date=payload.dueDate,
            )
        except ValueError as exc:
            raise HTTPException(status_code=422, detail=str(exc)) from exc
        except ValidationError as exc:
            raise HTTPException(status_code=400, detail=str(exc)) from exc
        except NotFoundError as exc:
            raise HTTPException(status_code=404, detail=str(exc)) from exc

    @app.patch("/api/boards/{board_id}/cards/{card_id}", response_model=Board)
    def update_card(
        request: Request,
        board_id: str,
        card_id: str,
        payload: UpdateCardRequest,
    ) -> Board:
        auth = _require_auth(request)
        try:
            clear_due_date = (
                "dueDate" in payload.model_fields_set and payload.dueDate is None
            )
            return request.app.state.repo.update_card(
                user_id=auth.user_id,
                board_api_id=board_id,
                card_api_id=card_id,
                title=payload.title,
                details=payload.details,
                priority=payload.priority,
                due_date=payload.dueDate,
                clear_due_date=clear_due_date,
            )
        except ValueError as exc:
            raise HTTPException(status_code=422, detail=str(exc)) from exc
        except ValidationError as exc:
            raise HTTPException(status_code=400, detail=str(exc)) from exc
        except NotFoundError as exc:
            raise HTTPException(status_code=404, detail=str(exc)) from exc

    @app.delete(
        "/api/boards/{board_id}/columns/{column_id}/cards/{card_id}",
        response_model=Board,
    )
    def remove_card(
        request: Request, board_id: str, column_id: str, card_id: str
    ) -> Board:
        auth = _require_auth(request)
        try:
            return request.app.state.repo.delete_card(
                auth.user_id, board_id, column_id, card_id
            )
        except ValueError as exc:
            raise HTTPException(status_code=422, detail=str(exc)) from exc
        except NotFoundError as exc:
            raise HTTPException(status_code=404, detail=str(exc)) from exc

    @app.post("/api/boards/{board_id}/cards/{card_id}/move", response_model=Board)
    def move_card(
        request: Request, board_id: str, card_id: str, payload: MoveCardRequest
    ) -> Board:
        auth = _require_auth(request)
        try:
            parse_api_id(payload.targetColumnId, "col")
            if payload.beforeCardId is not None:
                parse_api_id(payload.beforeCardId, "card")
            return request.app.state.repo.move_card(
                user_id=auth.user_id,
                board_api_id=board_id,
                card_api_id=card_id,
                target_column_api_id=payload.targetColumnId,
                before_card_api_id=payload.beforeCardId,
            )
        except ValueError as exc:
            raise HTTPException(status_code=422, detail=str(exc)) from exc
        except NotFoundError as exc:
            raise HTTPException(status_code=404, detail=str(exc)) from exc

    # ---- Card labels ----

    @app.put(
        "/api/boards/{board_id}/cards/{card_id}/labels", response_model=Board
    )
    def set_card_labels(
        request: Request,
        board_id: str,
        card_id: str,
        payload: SetCardLabelsRequest,
    ) -> Board:
        auth = _require_auth(request)
        try:
            return request.app.state.repo.set_card_labels(
                auth.user_id, board_id, card_id, payload.labelIds
            )
        except (NotFoundError, ValueError) as exc:
            raise HTTPException(status_code=404, detail=str(exc)) from exc

    # ---- Label CRUD ----

    @app.post(
        "/api/boards/{board_id}/labels", response_model=Label, status_code=201
    )
    def create_label(
        request: Request, board_id: str, payload: CreateLabelRequest
    ) -> Label:
        auth = _require_auth(request)
        try:
            return request.app.state.repo.create_label(
                auth.user_id, board_id, payload.name, payload.color
            )
        except (NotFoundError, ValueError) as exc:
            raise HTTPException(status_code=404, detail=str(exc)) from exc
        except ConflictError as exc:
            raise HTTPException(status_code=409, detail=str(exc)) from exc

    @app.patch(
        "/api/boards/{board_id}/labels/{label_id}", response_model=Label
    )
    def update_label(
        request: Request, board_id: str, label_id: str, payload: UpdateLabelRequest
    ) -> Label:
        auth = _require_auth(request)
        try:
            return request.app.state.repo.update_label(
                auth.user_id, board_id, label_id, payload.name, payload.color
            )
        except (NotFoundError, ValueError) as exc:
            raise HTTPException(status_code=404, detail=str(exc)) from exc
        except ValidationError as exc:
            raise HTTPException(status_code=400, detail=str(exc)) from exc
        except ConflictError as exc:
            raise HTTPException(status_code=409, detail=str(exc)) from exc

    @app.delete("/api/boards/{board_id}/labels/{label_id}", status_code=204)
    def delete_label(request: Request, board_id: str, label_id: str) -> None:
        auth = _require_auth(request)
        try:
            request.app.state.repo.delete_label(auth.user_id, board_id, label_id)
        except (NotFoundError, ValueError) as exc:
            raise HTTPException(status_code=404, detail=str(exc)) from exc

    # ---- AI ----

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

    @app.post(
        "/api/boards/{board_id}/ai/chat", response_model=AIChatResponse
    )
    def ai_chat(
        request: Request, board_id: str, payload: AIChatRequest
    ) -> AIChatResponse:
        auth = _require_auth(request)
        startup_error = request.app.state.ai_client_error
        if startup_error is not None:
            raise HTTPException(status_code=503, detail=str(startup_error))
        try:
            current_board = request.app.state.repo.get_board(auth.user_id, board_id)
            assistant_message, operations = request.app.state.ai_client.build_plan(
                board_snapshot=current_board.model_dump(),
                user_message=payload.message,
                conversation_history=[
                    {"role": m.role, "content": m.content} for m in payload.history
                ],
            )
            updated_board = request.app.state.repo.apply_ai_operations(
                auth.user_id, board_id, operations
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

    # ---- Utility ----

    @app.get("/api/hello")
    def hello() -> dict[str, str]:
        return {"message": "hello from fastapi"}

    @app.get("/health")
    def health_check() -> dict[str, str]:
        return {"status": "ok"}

    app.mount("/", StaticFiles(directory=static_dir, html=True), name="frontend")
    return app
