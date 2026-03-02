import sqlite3
from pathlib import Path

from app.db import (
    initialize_database,
    parse_api_id,
    sqlite_connection,
    to_card_api_id,
    to_column_api_id,
)
from app.schemas import AIOperation, Board, Card, Column


class NotFoundError(Exception):
    pass


class ValidationError(Exception):
    pass


class KanbanRepository:
    def __init__(self, db_path: Path):
        self.db_path = db_path

    def initialize(self) -> None:
        initialize_database(self.db_path)

    def get_board(self, username: str) -> Board:
        with sqlite_connection(self.db_path) as conn:
            board_id = _lookup_board_id(conn, username)
            return _build_board(conn, board_id)

    def rename_column(self, username: str, column_api_id: str, title: str) -> Board:
        title = title.strip()
        if not title:
            raise ValidationError("Column title is required.")

        column_id = parse_api_id(column_api_id, "col")
        with sqlite_connection(self.db_path) as conn:
            board_id = _lookup_board_id(conn, username)
            _ensure_column_in_board(conn, board_id, column_id)
            conn.execute(
                "UPDATE columns SET title = ?, updated_at = CURRENT_TIMESTAMP WHERE id = ?",
                (title, column_id),
            )
            conn.commit()
            return _build_board(conn, board_id)

    def create_card(self, username: str, column_api_id: str, title: str, details: str) -> Board:
        title = title.strip()
        if not title:
            raise ValidationError("Card title is required.")

        column_id = parse_api_id(column_api_id, "col")
        with sqlite_connection(self.db_path) as conn:
            board_id = _lookup_board_id(conn, username)
            _ensure_column_in_board(conn, board_id, column_id)

            max_position = conn.execute(
                "SELECT COALESCE(MAX(position), -1) AS max_position FROM card_placements WHERE column_id = ?",
                (column_id,),
            ).fetchone()["max_position"]
            next_position = int(max_position) + 1

            cursor = conn.execute(
                "INSERT INTO cards (board_id, title, details) VALUES (?, ?, ?)",
                (board_id, title, details.strip()),
            )
            card_id = int(cursor.lastrowid)

            conn.execute(
                "INSERT INTO card_placements (card_id, column_id, position) VALUES (?, ?, ?)",
                (card_id, column_id, next_position),
            )
            conn.commit()
            return _build_board(conn, board_id)

    def delete_card(self, username: str, column_api_id: str, card_api_id: str) -> Board:
        column_id = parse_api_id(column_api_id, "col")
        card_id = parse_api_id(card_api_id, "card")

        with sqlite_connection(self.db_path) as conn:
            board_id = _lookup_board_id(conn, username)
            _ensure_column_in_board(conn, board_id, column_id)

            placement = conn.execute(
                """
                SELECT cp.position
                FROM card_placements cp
                WHERE cp.card_id = ? AND cp.column_id = ?
                """,
                (card_id, column_id),
            ).fetchone()
            if not placement:
                raise NotFoundError("Card not found in the specified column.")

            old_position = int(placement["position"])

            conn.execute("DELETE FROM cards WHERE id = ? AND board_id = ?", (card_id, board_id))
            conn.execute(
                """
                UPDATE card_placements
                SET position = position - 1, updated_at = CURRENT_TIMESTAMP
                WHERE column_id = ? AND position > ?
                """,
                (column_id, old_position),
            )
            conn.commit()
            return _build_board(conn, board_id)

    def move_card(
        self,
        username: str,
        card_api_id: str,
        target_column_api_id: str,
        before_card_api_id: str | None,
    ) -> Board:
        card_id = parse_api_id(card_api_id, "card")
        target_column_id = parse_api_id(target_column_api_id, "col")

        with sqlite_connection(self.db_path) as conn:
            board_id = _lookup_board_id(conn, username)
            _ensure_column_in_board(conn, board_id, target_column_id)

            current = conn.execute(
                """
                SELECT cp.column_id, cp.position
                FROM card_placements cp
                JOIN cards c ON c.id = cp.card_id
                WHERE cp.card_id = ? AND c.board_id = ?
                """,
                (card_id, board_id),
            ).fetchone()
            if not current:
                raise NotFoundError("Card not found.")

            source_column_id = int(current["column_id"])
            source_position = int(current["position"])

            if before_card_api_id is None:
                max_position = conn.execute(
                    "SELECT COALESCE(MAX(position), -1) AS max_position FROM card_placements WHERE column_id = ?",
                    (target_column_id,),
                ).fetchone()["max_position"]
                insertion_position = int(max_position) + 1
            else:
                before_card_id = parse_api_id(before_card_api_id, "card")
                before_row = conn.execute(
                    """
                    SELECT cp.position
                    FROM card_placements cp
                    JOIN cards c ON c.id = cp.card_id
                    WHERE cp.card_id = ? AND cp.column_id = ? AND c.board_id = ?
                    """,
                    (before_card_id, target_column_id, board_id),
                ).fetchone()
                if not before_row:
                    raise NotFoundError("Reference card not found in target column.")
                insertion_position = int(before_row["position"])

            # Move card to a temporary safe slot to avoid unique(position) collisions
            # while compacting and expanding ordered lists.
            conn.execute(
                """
                UPDATE card_placements
                SET position = -1, updated_at = CURRENT_TIMESTAMP
                WHERE card_id = ?
                """,
                (card_id,),
            )

            conn.execute(
                """
                UPDATE card_placements
                SET position = position - 1, updated_at = CURRENT_TIMESTAMP
                WHERE column_id = ? AND position > ?
                """,
                (source_column_id, source_position),
            )

            if source_column_id == target_column_id and insertion_position > source_position:
                insertion_position -= 1

            conn.execute(
                """
                UPDATE card_placements
                SET position = position + 1, updated_at = CURRENT_TIMESTAMP
                WHERE column_id = ? AND position >= ?
                """,
                (target_column_id, insertion_position),
            )

            conn.execute(
                """
                UPDATE card_placements
                SET column_id = ?, position = ?, updated_at = CURRENT_TIMESTAMP
                WHERE card_id = ?
                """,
                (target_column_id, insertion_position, card_id),
            )
            conn.commit()
            return _build_board(conn, board_id)

    def apply_ai_operations(self, username: str, operations: list[AIOperation]) -> Board:
        with sqlite_connection(self.db_path) as conn:
            board_id = _lookup_board_id(conn, username)
            try:
                for operation in operations:
                    _apply_ai_operation(conn, board_id, operation)
            except Exception:
                conn.rollback()
                raise
            conn.commit()
            return _build_board(conn, board_id)


def _lookup_board_id(conn: sqlite3.Connection, username: str) -> int:
    row = conn.execute(
        """
        SELECT b.id
        FROM boards b
        JOIN users u ON u.id = b.user_id
        WHERE u.username = ?
        """,
        (username,),
    ).fetchone()
    if not row:
        raise NotFoundError("Board not found for user.")
    return int(row["id"])


def _ensure_column_in_board(conn: sqlite3.Connection, board_id: int, column_id: int) -> None:
    row = conn.execute(
        "SELECT id FROM columns WHERE id = ? AND board_id = ?",
        (column_id, board_id),
    ).fetchone()
    if not row:
        raise NotFoundError("Column not found.")


def _build_board(conn: sqlite3.Connection, board_id: int) -> Board:
    columns_rows = conn.execute(
        "SELECT id, title FROM columns WHERE board_id = ? ORDER BY position ASC",
        (board_id,),
    ).fetchall()

    cards_rows = conn.execute(
        """
        SELECT c.id, c.title, c.details, cp.column_id
        FROM cards c
        JOIN card_placements cp ON cp.card_id = c.id
        JOIN columns col ON col.id = cp.column_id
        WHERE c.board_id = ?
        ORDER BY col.position ASC, cp.position ASC
        """,
        (board_id,),
    ).fetchall()

    cards: dict[str, Card] = {}
    card_ids_by_column: dict[int, list[str]] = {int(row["id"]): [] for row in columns_rows}

    for row in cards_rows:
        card_api_id = to_card_api_id(int(row["id"]))
        cards[card_api_id] = Card(
            id=card_api_id,
            title=row["title"],
            details=row["details"],
        )
        card_ids_by_column[int(row["column_id"])].append(card_api_id)

    columns = [
        Column(
            id=to_column_api_id(int(row["id"])),
            title=row["title"],
            cardIds=card_ids_by_column[int(row["id"])],
        )
        for row in columns_rows
    ]

    return Board(columns=columns, cards=cards)


def _ensure_card_in_board(conn: sqlite3.Connection, board_id: int, card_id: int) -> None:
    row = conn.execute(
        "SELECT id FROM cards WHERE id = ? AND board_id = ?",
        (card_id, board_id),
    ).fetchone()
    if not row:
        raise NotFoundError("Card not found.")


def _delete_card_by_id(conn: sqlite3.Connection, board_id: int, card_id: int) -> None:
    placement = conn.execute(
        """
        SELECT cp.column_id, cp.position
        FROM card_placements cp
        JOIN cards c ON c.id = cp.card_id
        WHERE cp.card_id = ? AND c.board_id = ?
        """,
        (card_id, board_id),
    ).fetchone()
    if not placement:
        raise NotFoundError("Card not found.")

    column_id = int(placement["column_id"])
    old_position = int(placement["position"])
    conn.execute("DELETE FROM cards WHERE id = ? AND board_id = ?", (card_id, board_id))
    conn.execute(
        """
        UPDATE card_placements
        SET position = position - 1, updated_at = CURRENT_TIMESTAMP
        WHERE column_id = ? AND position > ?
        """,
        (column_id, old_position),
    )


def _move_card_by_id(
    conn: sqlite3.Connection,
    board_id: int,
    card_id: int,
    target_column_id: int,
    before_card_id: int | None,
) -> None:
    _ensure_column_in_board(conn, board_id, target_column_id)
    current = conn.execute(
        """
        SELECT cp.column_id, cp.position
        FROM card_placements cp
        JOIN cards c ON c.id = cp.card_id
        WHERE cp.card_id = ? AND c.board_id = ?
        """,
        (card_id, board_id),
    ).fetchone()
    if not current:
        raise NotFoundError("Card not found.")

    source_column_id = int(current["column_id"])
    source_position = int(current["position"])

    if before_card_id is None:
        max_position = conn.execute(
            "SELECT COALESCE(MAX(position), -1) AS max_position FROM card_placements WHERE column_id = ?",
            (target_column_id,),
        ).fetchone()["max_position"]
        insertion_position = int(max_position) + 1
    else:
        before_row = conn.execute(
            """
            SELECT cp.position
            FROM card_placements cp
            JOIN cards c ON c.id = cp.card_id
            WHERE cp.card_id = ? AND cp.column_id = ? AND c.board_id = ?
            """,
            (before_card_id, target_column_id, board_id),
        ).fetchone()
        if not before_row:
            raise NotFoundError("Reference card not found in target column.")
        insertion_position = int(before_row["position"])

    conn.execute(
        """
        UPDATE card_placements
        SET position = -1, updated_at = CURRENT_TIMESTAMP
        WHERE card_id = ?
        """,
        (card_id,),
    )
    conn.execute(
        """
        UPDATE card_placements
        SET position = position - 1, updated_at = CURRENT_TIMESTAMP
        WHERE column_id = ? AND position > ?
        """,
        (source_column_id, source_position),
    )
    if source_column_id == target_column_id and insertion_position > source_position:
        insertion_position -= 1
    conn.execute(
        """
        UPDATE card_placements
        SET position = position + 1, updated_at = CURRENT_TIMESTAMP
        WHERE column_id = ? AND position >= ?
        """,
        (target_column_id, insertion_position),
    )
    conn.execute(
        """
        UPDATE card_placements
        SET column_id = ?, position = ?, updated_at = CURRENT_TIMESTAMP
        WHERE card_id = ?
        """,
        (target_column_id, insertion_position, card_id),
    )


def _apply_ai_operation(conn: sqlite3.Connection, board_id: int, operation: AIOperation) -> None:
    if operation.type == "create_card":
        column_id = parse_api_id(operation.column_id or "", "col")
        _ensure_column_in_board(conn, board_id, column_id)
        max_position = conn.execute(
            "SELECT COALESCE(MAX(position), -1) AS max_position FROM card_placements WHERE column_id = ?",
            (column_id,),
        ).fetchone()["max_position"]
        next_position = int(max_position) + 1
        cursor = conn.execute(
            "INSERT INTO cards (board_id, title, details) VALUES (?, ?, ?)",
            (board_id, operation.title.strip(), (operation.details or "").strip()),
        )
        card_id = int(cursor.lastrowid)
        conn.execute(
            "INSERT INTO card_placements (card_id, column_id, position) VALUES (?, ?, ?)",
            (card_id, column_id, next_position),
        )
        return

    if operation.type == "update_card":
        card_id = parse_api_id(operation.card_id or "", "card")
        _ensure_card_in_board(conn, board_id, card_id)
        if operation.title is not None:
            title = operation.title.strip()
            if not title:
                raise ValidationError("Card title is required.")
            conn.execute(
                "UPDATE cards SET title = ?, updated_at = CURRENT_TIMESTAMP WHERE id = ? AND board_id = ?",
                (title, card_id, board_id),
            )
        if operation.details is not None:
            conn.execute(
                "UPDATE cards SET details = ?, updated_at = CURRENT_TIMESTAMP WHERE id = ? AND board_id = ?",
                (operation.details.strip(), card_id, board_id),
            )
        return

    if operation.type == "move_card":
        card_id = parse_api_id(operation.card_id or "", "card")
        target_column_id = parse_api_id(operation.column_id or "", "col")
        before_card_id = (
            parse_api_id(operation.before_card_id, "card")
            if operation.before_card_id is not None
            else None
        )
        _move_card_by_id(conn, board_id, card_id, target_column_id, before_card_id)
        return

    if operation.type == "delete_card":
        card_id = parse_api_id(operation.card_id or "", "card")
        _delete_card_by_id(conn, board_id, card_id)
        return

    if operation.type == "rename_column":
        column_id = parse_api_id(operation.column_id or "", "col")
        _ensure_column_in_board(conn, board_id, column_id)
        title = (operation.title or "").strip()
        if not title:
            raise ValidationError("Column title is required.")
        conn.execute(
            "UPDATE columns SET title = ?, updated_at = CURRENT_TIMESTAMP WHERE id = ?",
            (title, column_id),
        )
        return

    raise ValidationError("Unsupported operation type.")
