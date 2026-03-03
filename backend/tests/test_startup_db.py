import sqlite3
from pathlib import Path

from app.db import initialize_database, sqlite_connection


def test_initialize_creates_tables(temp_db_path: Path) -> None:
    initialize_database(temp_db_path)
    assert temp_db_path.exists()

    with sqlite_connection(temp_db_path) as conn:
        tables = conn.execute(
            "SELECT name FROM sqlite_master WHERE type='table'"
        ).fetchall()
        table_names = {row["name"] for row in tables}
        assert "users" in table_names
        assert "boards" in table_names
        assert "columns" in table_names
        assert "cards" in table_names
        assert "card_placements" in table_names
        assert "labels" in table_names
        assert "card_labels" in table_names


def test_seed_user_exists(temp_db_path: Path) -> None:
    initialize_database(temp_db_path)

    with sqlite_connection(temp_db_path) as conn:
        user = conn.execute(
            "SELECT username, display_name FROM users WHERE username = ?",
            ("user",),
        ).fetchone()
        assert user is not None
        assert user["display_name"] == "Demo User"


def test_seed_board_and_columns(temp_db_path: Path) -> None:
    initialize_database(temp_db_path)

    with sqlite_connection(temp_db_path) as conn:
        board = conn.execute("SELECT * FROM boards").fetchone()
        assert board["name"] == "My Board"
        assert board["description"] == "Default project board"

        cols = conn.execute(
            "SELECT title FROM columns WHERE board_id = ? ORDER BY position",
            (board["id"],),
        ).fetchall()
        assert [c["title"] for c in cols] == [
            "Backlog", "Discovery", "In Progress", "Review", "Done"
        ]


def test_seed_labels(temp_db_path: Path) -> None:
    initialize_database(temp_db_path)

    with sqlite_connection(temp_db_path) as conn:
        labels = conn.execute("SELECT name, color FROM labels ORDER BY name").fetchall()
        assert len(labels) == 5
        names = {l["name"] for l in labels}
        assert "Bug" in names
        assert "Feature" in names


def test_seed_cards_have_priority(temp_db_path: Path) -> None:
    initialize_database(temp_db_path)

    with sqlite_connection(temp_db_path) as conn:
        cards = conn.execute("SELECT title, priority FROM cards").fetchall()
        priorities = {c["priority"] for c in cards}
        assert "medium" in priorities
        assert "high" in priorities


def test_reinitialize_is_idempotent(temp_db_path: Path) -> None:
    initialize_database(temp_db_path)
    initialize_database(temp_db_path)

    with sqlite_connection(temp_db_path) as conn:
        users = conn.execute("SELECT * FROM users").fetchall()
        assert len(users) == 1


def test_password_is_hashed(temp_db_path: Path) -> None:
    initialize_database(temp_db_path)

    with sqlite_connection(temp_db_path) as conn:
        user = conn.execute("SELECT password_hash FROM users WHERE username = 'user'").fetchone()
        assert ":" in user["password_hash"]
        assert user["password_hash"] != "password"
