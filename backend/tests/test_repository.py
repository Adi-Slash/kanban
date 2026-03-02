from app.repository import KanbanRepository


def _first_column_id(board: dict) -> str:
    return board["columns"][0]["id"]


def _first_card_id(board: dict) -> str:
    return board["columns"][0]["cardIds"][0]


def test_repository_reads_seeded_board(temp_db_path) -> None:
    repo = KanbanRepository(temp_db_path)
    repo.initialize()

    board = repo.get_board("user")

    assert len(board.columns) == 5
    assert board.columns[0].title == "Backlog"
    assert len(board.cards) >= 8


def test_repository_create_move_delete_card(temp_db_path) -> None:
    repo = KanbanRepository(temp_db_path)
    repo.initialize()

    initial = repo.get_board("user")
    source_column_id = initial.columns[0].id
    target_column_id = initial.columns[1].id

    after_create = repo.create_card("user", source_column_id, "Repo card", "Repo details")
    created_id = after_create.columns[0].cardIds[-1]
    assert after_create.cards[created_id].title == "Repo card"

    after_move = repo.move_card("user", created_id, target_column_id, None)
    assert created_id in after_move.columns[1].cardIds

    after_delete = repo.delete_card("user", target_column_id, created_id)
    assert created_id not in after_delete.cards
