from pydantic import BaseModel, Field


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
