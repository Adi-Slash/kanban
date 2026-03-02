from typing import Literal

from pydantic import BaseModel, Field, model_validator


class Card(BaseModel):
    id: str
    title: str
    details: str


class Column(BaseModel):
    id: str
    title: str
    cardIds: list[str]


class Board(BaseModel):
    columns: list[Column]
    cards: dict[str, Card]


class RenameColumnRequest(BaseModel):
    title: str = Field(min_length=1, max_length=200)


class CreateCardRequest(BaseModel):
    title: str = Field(min_length=1, max_length=200)
    details: str = Field(default="", max_length=5000)


class MoveCardRequest(BaseModel):
    targetColumnId: str
    beforeCardId: str | None = None


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
