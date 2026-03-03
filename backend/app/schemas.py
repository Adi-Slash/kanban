from typing import Literal

from pydantic import BaseModel, Field, model_validator


class Label(BaseModel):
    id: str
    name: str
    color: str


class Card(BaseModel):
    id: str
    title: str
    details: str
    priority: Literal["low", "medium", "high", "urgent"] = "medium"
    dueDate: str | None = None
    labelIds: list[str] = Field(default_factory=list)


class Column(BaseModel):
    id: str
    title: str
    cardIds: list[str]


class Board(BaseModel):
    id: str
    name: str
    description: str = ""
    columns: list[Column]
    cards: dict[str, Card]
    labels: list[Label] = Field(default_factory=list)


class BoardSummary(BaseModel):
    id: str
    name: str
    description: str = ""
    columnCount: int
    cardCount: int
    updatedAt: str


class RegisterRequest(BaseModel):
    username: str = Field(min_length=2, max_length=50)
    password: str = Field(min_length=4, max_length=200)
    displayName: str = Field(default="", max_length=100)


class LoginRequest(BaseModel):
    username: str = Field(min_length=1)
    password: str = Field(min_length=1)


class ProfileResponse(BaseModel):
    username: str
    displayName: str


class UpdateProfileRequest(BaseModel):
    displayName: str = Field(max_length=100)


class CreateBoardRequest(BaseModel):
    name: str = Field(min_length=1, max_length=200)
    description: str = Field(default="", max_length=1000)


class UpdateBoardRequest(BaseModel):
    name: str | None = Field(default=None, min_length=1, max_length=200)
    description: str | None = Field(default=None, max_length=1000)


class RenameColumnRequest(BaseModel):
    title: str = Field(min_length=1, max_length=200)


class CreateCardRequest(BaseModel):
    title: str = Field(min_length=1, max_length=200)
    details: str = Field(default="", max_length=5000)
    priority: Literal["low", "medium", "high", "urgent"] = "medium"
    dueDate: str | None = None


class UpdateCardRequest(BaseModel):
    title: str | None = Field(default=None, min_length=1, max_length=200)
    details: str | None = Field(default=None, max_length=5000)
    priority: Literal["low", "medium", "high", "urgent"] | None = None
    dueDate: str | None = None


class MoveCardRequest(BaseModel):
    targetColumnId: str
    beforeCardId: str | None = None


class SetCardLabelsRequest(BaseModel):
    labelIds: list[str]


class CreateLabelRequest(BaseModel):
    name: str = Field(min_length=1, max_length=50)
    color: str = Field(min_length=4, max_length=9)


class UpdateLabelRequest(BaseModel):
    name: str | None = Field(default=None, min_length=1, max_length=50)
    color: str | None = Field(default=None, min_length=4, max_length=9)


class AISmokeResponse(BaseModel):
    assistantMessage: str
    model: str


class AIChatHistoryMessage(BaseModel):
    role: Literal["user", "assistant"]
    content: str = Field(min_length=1, max_length=5000)


class AIChatRequest(BaseModel):
    message: str = Field(min_length=1, max_length=5000)
    history: list[AIChatHistoryMessage] = Field(default_factory=list)


class AIOperation(BaseModel):
    type: Literal[
        "create_card",
        "update_card",
        "move_card",
        "delete_card",
        "rename_column",
    ]
    column_id: str | None = None
    card_id: str | None = None
    title: str | None = Field(default=None, max_length=200)
    details: str | None = Field(default=None, max_length=5000)
    before_card_id: str | None = None

    @model_validator(mode="after")
    def validate_required_fields(self):
        if self.type == "create_card":
            if not self.column_id:
                raise ValueError("create_card requires column_id")
            if not self.title or not self.title.strip():
                raise ValueError("create_card requires title")
        elif self.type == "update_card":
            if not self.card_id:
                raise ValueError("update_card requires card_id")
            if self.title is None and self.details is None:
                raise ValueError("update_card requires title and/or details")
        elif self.type == "move_card":
            if not self.card_id:
                raise ValueError("move_card requires card_id")
            if not self.column_id:
                raise ValueError("move_card requires column_id")
        elif self.type == "delete_card":
            if not self.card_id:
                raise ValueError("delete_card requires card_id")
        elif self.type == "rename_column":
            if not self.column_id:
                raise ValueError("rename_column requires column_id")
            if not self.title or not self.title.strip():
                raise ValueError("rename_column requires title")
        return self


class AIPlan(BaseModel):
    assistant_message: str = Field(min_length=1, max_length=5000)
    operations: list[AIOperation] = Field(default_factory=list)


class AIChatResponse(BaseModel):
    assistantMessage: str
    operations: list[AIOperation]
    board: Board
