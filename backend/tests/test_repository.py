from pathlib import Path

import pytest

from app.repository import ConflictError, KanbanRepository, NotFoundError, ValidationError


@pytest.fixture
def repo(temp_db_path: Path) -> KanbanRepository:
    r = KanbanRepository(temp_db_path)
    r.initialize()
    return r


@pytest.fixture
def user_id(repo: KanbanRepository) -> int:
    return repo.authenticate_user("user", "password")


@pytest.fixture
def default_board_id(repo: KanbanRepository, user_id: int) -> str:
    boards = repo.list_boards(user_id)
    return boards[0].id


def test_register_and_authenticate(repo) -> None:
    uid = repo.register_user("alice", "secret123", "Alice")
    assert uid > 0
    assert repo.authenticate_user("alice", "secret123") == uid
    assert repo.authenticate_user("alice", "wrong") is None


def test_register_duplicate_username(repo) -> None:
    with pytest.raises(ConflictError):
        repo.register_user("user", "password")


def test_list_boards(repo, user_id) -> None:
    boards = repo.list_boards(user_id)
    assert len(boards) == 1
    assert boards[0].name == "My Board"
    assert boards[0].columnCount == 5
    assert boards[0].cardCount == 8


def test_create_board(repo, user_id) -> None:
    result = repo.create_board(user_id, "New Board", "Description")
    assert result.name == "New Board"
    assert result.description == "Description"
    assert result.columnCount == 5
    assert result.cardCount == 0

    boards = repo.list_boards(user_id)
    assert len(boards) == 2


def test_get_board(repo, user_id, default_board_id) -> None:
    board = repo.get_board(user_id, default_board_id)
    assert board.id == default_board_id
    assert len(board.columns) == 5
    assert len(board.cards) == 8
    assert len(board.labels) == 5


def test_update_board(repo, user_id, default_board_id) -> None:
    result = repo.update_board(
        user_id, default_board_id, name="Updated", description="New desc"
    )
    assert result.name == "Updated"
    assert result.description == "New desc"


def test_delete_board(repo, user_id) -> None:
    created = repo.create_board(user_id, "Temp")
    repo.delete_board(user_id, created.id)
    boards = repo.list_boards(user_id)
    assert not any(b.id == created.id for b in boards)


def test_rename_column(repo, user_id, default_board_id) -> None:
    board = repo.get_board(user_id, default_board_id)
    col_id = board.columns[0].id
    updated = repo.rename_column(user_id, default_board_id, col_id, "Renamed")
    assert updated.columns[0].title == "Renamed"


def test_create_card_with_priority(repo, user_id, default_board_id) -> None:
    board = repo.get_board(user_id, default_board_id)
    col_id = board.columns[0].id
    updated = repo.create_card(
        user_id, default_board_id, col_id,
        title="Priority Card", details="", priority="urgent", due_date="2026-12-31",
    )
    new_card_id = updated.columns[0].cardIds[-1]
    card = updated.cards[new_card_id]
    assert card.title == "Priority Card"
    assert card.priority == "urgent"
    assert card.dueDate == "2026-12-31"


def test_update_card(repo, user_id, default_board_id) -> None:
    board = repo.get_board(user_id, default_board_id)
    card_id = board.columns[0].cardIds[0]
    updated = repo.update_card(
        user_id, default_board_id, card_id,
        title="New Title", priority="high",
    )
    assert updated.cards[card_id].title == "New Title"
    assert updated.cards[card_id].priority == "high"


def test_delete_card(repo, user_id, default_board_id) -> None:
    board = repo.get_board(user_id, default_board_id)
    col_id = board.columns[0].id
    card_id = board.columns[0].cardIds[0]
    updated = repo.delete_card(user_id, default_board_id, col_id, card_id)
    assert card_id not in updated.cards


def test_move_card(repo, user_id, default_board_id) -> None:
    board = repo.get_board(user_id, default_board_id)
    card_id = board.columns[0].cardIds[0]
    target_col_id = board.columns[3].id
    updated = repo.move_card(
        user_id, default_board_id, card_id, target_col_id, None
    )
    assert card_id in updated.columns[3].cardIds


def test_create_and_set_labels(repo, user_id, default_board_id) -> None:
    label = repo.create_label(user_id, default_board_id, "Test Label", "#ff0000")
    assert label.name == "Test Label"

    board = repo.get_board(user_id, default_board_id)
    card_id = board.columns[0].cardIds[0]
    updated = repo.set_card_labels(
        user_id, default_board_id, card_id, [label.id]
    )
    assert label.id in updated.cards[card_id].labelIds


def test_board_not_found_for_wrong_user(repo) -> None:
    uid = repo.register_user("bob", "bobpass")
    boards = repo.list_boards(uid)
    assert len(boards) == 0

    user_id = repo.authenticate_user("user", "password")
    user_boards = repo.list_boards(user_id)
    board_id = user_boards[0].id

    with pytest.raises(NotFoundError):
        repo.get_board(uid, board_id)


def test_ai_operations_transactional(repo, user_id, default_board_id) -> None:
    from app.schemas import AIOperation

    board = repo.get_board(user_id, default_board_id)
    col_id = board.columns[0].id

    ops = [
        AIOperation(type="create_card", column_id=col_id, title="AI Card"),
        AIOperation(type="create_card", column_id="col-99999", title="Bad Card"),
    ]
    with pytest.raises(NotFoundError):
        repo.apply_ai_operations(user_id, default_board_id, ops)

    after = repo.get_board(user_id, default_board_id)
    assert len(after.cards) == len(board.cards)
