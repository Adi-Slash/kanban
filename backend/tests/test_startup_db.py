import sqlite3


def test_startup_creates_database_and_tables(client, temp_db_path) -> None:
    # Trigger startup and ensure a DB file is created.
    assert temp_db_path.exists()

    with sqlite3.connect(temp_db_path) as conn:
        tables = {
            row[0]
            for row in conn.execute(
                "SELECT name FROM sqlite_master WHERE type='table'"
            ).fetchall()
        }

    assert {"users", "boards", "columns", "cards", "card_placements"}.issubset(tables)
