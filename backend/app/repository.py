import sqlite3
from pathlib import Path

from app.db import (
    DEFAULT_COLUMNS,
    hash_password,
    initialize_database,
    parse_api_id,
    sqlite_connection,
    to_board_api_id,
    to_card_api_id,
    to_column_api_id,
    to_label_api_id,
    verify_password,
)
from app.schemas import AIOperation, Board, BoardSummary, Card, Column, Label


class NotFoundError(Exception):
    pass


class ValidationError(Exception):
    pass


class ConflictError(Exception):
    pass


class KanbanRepository:
    def __init__(self, db_path: Path):
        self.db_path = db_path

    def initialize(self) -> None:
        initialize_database(self.db_path)

    # ---- User management ----

    def register_user(
        self, username: str, password: str, display_name: str = ""
    ) -> int:
        with sqlite_connection(self.db_path) as conn:
            existing = conn.execute(
                "SELECT id FROM users WHERE username = ?", (username,)
            ).fetchone()
            if existing:
                raise ConflictError("Username already taken.")
            password_hash = hash_password(password)
            cursor = conn.execute(
                "INSERT INTO users (username, display_name, password_hash) VALUES (?, ?, ?)",
                (username, display_name, password_hash),
            )
            user_id = int(cursor.lastrowid)
            conn.commit()
            return user_id

    def authenticate_user(self, username: str, password: str) -> int | None:
        with sqlite_connection(self.db_path) as conn:
            row = conn.execute(
                "SELECT id, password_hash FROM users WHERE username = ?",
                (username,),
            ).fetchone()
            if not row:
                return None
            if not verify_password(password, row["password_hash"]):
                return None
            return int(row["id"])

    def get_user_profile(self, user_id: int) -> dict:
        with sqlite_connection(self.db_path) as conn:
            row = conn.execute(
                "SELECT username, display_name FROM users WHERE id = ?",
                (user_id,),
            ).fetchone()
            if not row:
                raise NotFoundError("User not found.")
            return {"username": row["username"], "displayName": row["display_name"]}

    def update_user_profile(self, user_id: int, display_name: str) -> None:
        with sqlite_connection(self.db_path) as conn:
            conn.execute(
                "UPDATE users SET display_name = ? WHERE id = ?",
                (display_name, user_id),
            )
            conn.commit()

    # ---- Board CRUD ----

    def list_boards(self, user_id: int) -> list[BoardSummary]:
        with sqlite_connection(self.db_path) as conn:
            rows = conn.execute(
                """
                SELECT b.id, b.name, b.description, b.updated_at,
                       (SELECT COUNT(*) FROM columns WHERE board_id = b.id) AS col_count,
                       (SELECT COUNT(*) FROM cards WHERE board_id = b.id) AS card_count
                FROM boards b
                WHERE b.user_id = ?
                ORDER BY b.updated_at DESC
                """,
                (user_id,),
            ).fetchall()
            return [
                BoardSummary(
                    id=to_board_api_id(int(row["id"])),
                    name=row["name"],
                    description=row["description"],
                    columnCount=int(row["col_count"]),
                    cardCount=int(row["card_count"]),
                    updatedAt=row["updated_at"],
                )
                for row in rows
            ]

    def create_board(
        self, user_id: int, name: str, description: str = ""
    ) -> BoardSummary:
        with sqlite_connection(self.db_path) as conn:
            cursor = conn.execute(
                "INSERT INTO boards (user_id, name, description) VALUES (?, ?, ?)",
                (user_id, name.strip(), description.strip()),
            )
            board_id = int(cursor.lastrowid)
            for position, (slug, title) in enumerate(DEFAULT_COLUMNS):
                conn.execute(
                    "INSERT INTO columns (board_id, slug, title, position) VALUES (?, ?, ?, ?)",
                    (board_id, slug, title, position),
                )
            conn.commit()
            return BoardSummary(
                id=to_board_api_id(board_id),
                name=name.strip(),
                description=description.strip(),
                columnCount=len(DEFAULT_COLUMNS),
                cardCount=0,
                updatedAt=conn.execute(
                    "SELECT updated_at FROM boards WHERE id = ?", (board_id,)
                ).fetchone()["updated_at"],
            )

    def get_board(self, user_id: int, board_api_id: str) -> Board:
        with sqlite_connection(self.db_path) as conn:
            board_id = _resolve_board(conn, user_id, board_api_id)
            return _build_board(conn, board_id)

    def update_board(
        self,
        user_id: int,
        board_api_id: str,
        name: str | None = None,
        description: str | None = None,
    ) -> BoardSummary:
        with sqlite_connection(self.db_path) as conn:
            board_id = _resolve_board(conn, user_id, board_api_id)
            if name is not None:
                name = name.strip()
                if not name:
                    raise ValidationError("Board name is required.")
                conn.execute(
                    "UPDATE boards SET name = ?, updated_at = CURRENT_TIMESTAMP WHERE id = ?",
                    (name, board_id),
                )
            if description is not None:
                conn.execute(
                    "UPDATE boards SET description = ?, updated_at = CURRENT_TIMESTAMP WHERE id = ?",
                    (description.strip(), board_id),
                )
            conn.commit()
            row = conn.execute(
                """
                SELECT b.name, b.description, b.updated_at,
                       (SELECT COUNT(*) FROM columns WHERE board_id = b.id) AS col_count,
                       (SELECT COUNT(*) FROM cards WHERE board_id = b.id) AS card_count
                FROM boards b WHERE b.id = ?
                """,
                (board_id,),
            ).fetchone()
            return BoardSummary(
                id=board_api_id,
                name=row["name"],
                description=row["description"],
                columnCount=int(row["col_count"]),
                cardCount=int(row["card_count"]),
                updatedAt=row["updated_at"],
            )

    def delete_board(self, user_id: int, board_api_id: str) -> None:
        with sqlite_connection(self.db_path) as conn:
            board_id = _resolve_board(conn, user_id, board_api_id)
            conn.execute("DELETE FROM boards WHERE id = ?", (board_id,))
            conn.commit()

    # ---- Column operations ----

    def rename_column(
        self, user_id: int, board_api_id: str, column_api_id: str, title: str
    ) -> Board:
        title = title.strip()
        if not title:
            raise ValidationError("Column title is required.")
        column_id = parse_api_id(column_api_id, "col")
        with sqlite_connection(self.db_path) as conn:
            board_id = _resolve_board(conn, user_id, board_api_id)
            _ensure_column_in_board(conn, board_id, column_id)
            conn.execute(
                "UPDATE columns SET title = ?, updated_at = CURRENT_TIMESTAMP WHERE id = ?",
                (title, column_id),
            )
            conn.commit()
            return _build_board(conn, board_id)

    # ---- Card CRUD ----

    def create_card(
        self,
        user_id: int,
        board_api_id: str,
        column_api_id: str,
        title: str,
        details: str,
        priority: str = "medium",
        due_date: str | None = None,
    ) -> Board:
        title = title.strip()
        if not title:
            raise ValidationError("Card title is required.")
        column_id = parse_api_id(column_api_id, "col")
        with sqlite_connection(self.db_path) as conn:
            board_id = _resolve_board(conn, user_id, board_api_id)
            _ensure_column_in_board(conn, board_id, column_id)
            max_pos = conn.execute(
                "SELECT COALESCE(MAX(position), -1) AS mp FROM card_placements WHERE column_id = ?",
                (column_id,),
            ).fetchone()["mp"]
            cursor = conn.execute(
                "INSERT INTO cards (board_id, title, details, priority, due_date) VALUES (?, ?, ?, ?, ?)",
                (board_id, title, details.strip(), priority, due_date),
            )
            card_id = int(cursor.lastrowid)
            conn.execute(
                "INSERT INTO card_placements (card_id, column_id, position) VALUES (?, ?, ?)",
                (card_id, column_id, int(max_pos) + 1),
            )
            conn.commit()
            return _build_board(conn, board_id)

    def update_card(
        self,
        user_id: int,
        board_api_id: str,
        card_api_id: str,
        *,
        title: str | None = None,
        details: str | None = None,
        priority: str | None = None,
        due_date: str | None = None,
        clear_due_date: bool = False,
    ) -> Board:
        card_id = parse_api_id(card_api_id, "card")
        with sqlite_connection(self.db_path) as conn:
            board_id = _resolve_board(conn, user_id, board_api_id)
            _ensure_card_in_board(conn, board_id, card_id)
            if title is not None:
                t = title.strip()
                if not t:
                    raise ValidationError("Card title is required.")
                conn.execute(
                    "UPDATE cards SET title = ?, updated_at = CURRENT_TIMESTAMP WHERE id = ?",
                    (t, card_id),
                )
            if details is not None:
                conn.execute(
                    "UPDATE cards SET details = ?, updated_at = CURRENT_TIMESTAMP WHERE id = ?",
                    (details.strip(), card_id),
                )
            if priority is not None:
                conn.execute(
                    "UPDATE cards SET priority = ?, updated_at = CURRENT_TIMESTAMP WHERE id = ?",
                    (priority, card_id),
                )
            if due_date is not None:
                conn.execute(
                    "UPDATE cards SET due_date = ?, updated_at = CURRENT_TIMESTAMP WHERE id = ?",
                    (due_date, card_id),
                )
            elif clear_due_date:
                conn.execute(
                    "UPDATE cards SET due_date = NULL, updated_at = CURRENT_TIMESTAMP WHERE id = ?",
                    (card_id,),
                )
            conn.commit()
            return _build_board(conn, board_id)

    def delete_card(
        self, user_id: int, board_api_id: str, column_api_id: str, card_api_id: str
    ) -> Board:
        column_id = parse_api_id(column_api_id, "col")
        card_id = parse_api_id(card_api_id, "card")
        with sqlite_connection(self.db_path) as conn:
            board_id = _resolve_board(conn, user_id, board_api_id)
            _ensure_column_in_board(conn, board_id, column_id)
            _delete_card_by_id(conn, board_id, card_id, column_id)
            conn.commit()
            return _build_board(conn, board_id)

    def move_card(
        self,
        user_id: int,
        board_api_id: str,
        card_api_id: str,
        target_column_api_id: str,
        before_card_api_id: str | None,
    ) -> Board:
        card_id = parse_api_id(card_api_id, "card")
        target_column_id = parse_api_id(target_column_api_id, "col")
        before_card_id = (
            parse_api_id(before_card_api_id, "card") if before_card_api_id else None
        )
        with sqlite_connection(self.db_path) as conn:
            board_id = _resolve_board(conn, user_id, board_api_id)
            _ensure_column_in_board(conn, board_id, target_column_id)
            _move_card_by_id(conn, board_id, card_id, target_column_id, before_card_id)
            conn.commit()
            return _build_board(conn, board_id)

    # ---- Label CRUD ----

    def create_label(
        self, user_id: int, board_api_id: str, name: str, color: str
    ) -> Label:
        with sqlite_connection(self.db_path) as conn:
            board_id = _resolve_board(conn, user_id, board_api_id)
            existing = conn.execute(
                "SELECT id FROM labels WHERE board_id = ? AND name = ?",
                (board_id, name.strip()),
            ).fetchone()
            if existing:
                raise ConflictError("Label name already exists on this board.")
            cursor = conn.execute(
                "INSERT INTO labels (board_id, name, color) VALUES (?, ?, ?)",
                (board_id, name.strip(), color.strip()),
            )
            conn.commit()
            return Label(
                id=to_label_api_id(int(cursor.lastrowid)),
                name=name.strip(),
                color=color.strip(),
            )

    def update_label(
        self,
        user_id: int,
        board_api_id: str,
        label_api_id: str,
        name: str | None = None,
        color: str | None = None,
    ) -> Label:
        label_id = parse_api_id(label_api_id, "label")
        with sqlite_connection(self.db_path) as conn:
            board_id = _resolve_board(conn, user_id, board_api_id)
            row = conn.execute(
                "SELECT id, name, color FROM labels WHERE id = ? AND board_id = ?",
                (label_id, board_id),
            ).fetchone()
            if not row:
                raise NotFoundError("Label not found.")
            if name is not None:
                n = name.strip()
                if not n:
                    raise ValidationError("Label name is required.")
                dup = conn.execute(
                    "SELECT id FROM labels WHERE board_id = ? AND name = ? AND id != ?",
                    (board_id, n, label_id),
                ).fetchone()
                if dup:
                    raise ConflictError("Label name already exists on this board.")
                conn.execute("UPDATE labels SET name = ? WHERE id = ?", (n, label_id))
            if color is not None:
                conn.execute(
                    "UPDATE labels SET color = ? WHERE id = ?", (color.strip(), label_id)
                )
            conn.commit()
            updated = conn.execute(
                "SELECT name, color FROM labels WHERE id = ?", (label_id,)
            ).fetchone()
            return Label(
                id=label_api_id,
                name=updated["name"],
                color=updated["color"],
            )

    def delete_label(
        self, user_id: int, board_api_id: str, label_api_id: str
    ) -> None:
        label_id = parse_api_id(label_api_id, "label")
        with sqlite_connection(self.db_path) as conn:
            board_id = _resolve_board(conn, user_id, board_api_id)
            row = conn.execute(
                "SELECT id FROM labels WHERE id = ? AND board_id = ?",
                (label_id, board_id),
            ).fetchone()
            if not row:
                raise NotFoundError("Label not found.")
            conn.execute("DELETE FROM labels WHERE id = ?", (label_id,))
            conn.commit()

    def set_card_labels(
        self,
        user_id: int,
        board_api_id: str,
        card_api_id: str,
        label_api_ids: list[str],
    ) -> Board:
        card_id = parse_api_id(card_api_id, "card")
        label_ids = [parse_api_id(lid, "label") for lid in label_api_ids]
        with sqlite_connection(self.db_path) as conn:
            board_id = _resolve_board(conn, user_id, board_api_id)
            _ensure_card_in_board(conn, board_id, card_id)
            for lid in label_ids:
                row = conn.execute(
                    "SELECT id FROM labels WHERE id = ? AND board_id = ?",
                    (lid, board_id),
                ).fetchone()
                if not row:
                    raise NotFoundError(f"Label label-{lid} not found.")
            conn.execute("DELETE FROM card_labels WHERE card_id = ?", (card_id,))
            for lid in label_ids:
                conn.execute(
                    "INSERT INTO card_labels (card_id, label_id) VALUES (?, ?)",
                    (card_id, lid),
                )
            conn.commit()
            return _build_board(conn, board_id)

    # ---- AI operations ----

    def apply_ai_operations(
        self, user_id: int, board_api_id: str, operations: list[AIOperation]
    ) -> Board:
        with sqlite_connection(self.db_path) as conn:
            board_id = _resolve_board(conn, user_id, board_api_id)
            try:
                for op in operations:
                    _validate_ai_operation(conn, board_id, op)
                for op in operations:
                    _apply_ai_operation(conn, board_id, op)
            except (NotFoundError, ValidationError, ValueError):
                conn.rollback()
                raise
            except Exception:
                conn.rollback()
                raise
            conn.commit()
            return _build_board(conn, board_id)


# ---- Private helpers ----


def _resolve_board(conn: sqlite3.Connection, user_id: int, board_api_id: str) -> int:
    board_id = parse_api_id(board_api_id, "board")
    row = conn.execute(
        "SELECT id FROM boards WHERE id = ? AND user_id = ?",
        (board_id, user_id),
    ).fetchone()
    if not row:
        raise NotFoundError("Board not found.")
    return board_id


def _ensure_column_in_board(
    conn: sqlite3.Connection, board_id: int, column_id: int
) -> None:
    row = conn.execute(
        "SELECT id FROM columns WHERE id = ? AND board_id = ?",
        (column_id, board_id),
    ).fetchone()
    if not row:
        raise NotFoundError("Column not found.")


def _ensure_card_in_board(
    conn: sqlite3.Connection, board_id: int, card_id: int
) -> None:
    row = conn.execute(
        "SELECT id FROM cards WHERE id = ? AND board_id = ?",
        (card_id, board_id),
    ).fetchone()
    if not row:
        raise NotFoundError("Card not found.")


def _build_board(conn: sqlite3.Connection, board_id: int) -> Board:
    board_row = conn.execute(
        "SELECT id, name, description FROM boards WHERE id = ?", (board_id,)
    ).fetchone()

    columns_rows = conn.execute(
        "SELECT id, title FROM columns WHERE board_id = ? ORDER BY position ASC",
        (board_id,),
    ).fetchall()

    cards_rows = conn.execute(
        """
        SELECT c.id, c.title, c.details, c.priority, c.due_date, cp.column_id
        FROM cards c
        JOIN card_placements cp ON cp.card_id = c.id
        JOIN columns col ON col.id = cp.column_id
        WHERE c.board_id = ?
        ORDER BY col.position ASC, cp.position ASC
        """,
        (board_id,),
    ).fetchall()

    labels_rows = conn.execute(
        "SELECT id, name, color FROM labels WHERE board_id = ? ORDER BY name",
        (board_id,),
    ).fetchall()

    card_labels_rows = conn.execute(
        """
        SELECT cl.card_id, cl.label_id
        FROM card_labels cl
        JOIN cards c ON c.id = cl.card_id
        WHERE c.board_id = ?
        """,
        (board_id,),
    ).fetchall()

    card_label_map: dict[int, list[str]] = {}
    for row in card_labels_rows:
        cid = int(row["card_id"])
        card_label_map.setdefault(cid, []).append(
            to_label_api_id(int(row["label_id"]))
        )

    labels = [
        Label(
            id=to_label_api_id(int(row["id"])),
            name=row["name"],
            color=row["color"],
        )
        for row in labels_rows
    ]

    cards: dict[str, Card] = {}
    card_ids_by_column: dict[int, list[str]] = {
        int(row["id"]): [] for row in columns_rows
    }

    for row in cards_rows:
        db_card_id = int(row["id"])
        card_api_id = to_card_api_id(db_card_id)
        cards[card_api_id] = Card(
            id=card_api_id,
            title=row["title"],
            details=row["details"],
            priority=row["priority"],
            dueDate=row["due_date"],
            labelIds=card_label_map.get(db_card_id, []),
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

    return Board(
        id=to_board_api_id(board_id),
        name=board_row["name"],
        description=board_row["description"],
        columns=columns,
        cards=cards,
        labels=labels,
    )


def _delete_card_by_id(
    conn: sqlite3.Connection,
    board_id: int,
    card_id: int,
    column_id: int | None = None,
) -> None:
    query = """
        SELECT cp.column_id, cp.position
        FROM card_placements cp
        JOIN cards c ON c.id = cp.card_id
        WHERE cp.card_id = ? AND c.board_id = ?
    """
    params: tuple = (card_id, board_id)
    if column_id is not None:
        query += " AND cp.column_id = ?"
        params = (card_id, board_id, column_id)

    placement = conn.execute(query, params).fetchone()
    if not placement:
        if column_id is not None:
            raise NotFoundError("Card not found in the specified column.")
        raise NotFoundError("Card not found.")

    actual_column_id = int(placement["column_id"])
    old_position = int(placement["position"])
    conn.execute("DELETE FROM cards WHERE id = ? AND board_id = ?", (card_id, board_id))
    conn.execute(
        """
        UPDATE card_placements
        SET position = position - 1, updated_at = CURRENT_TIMESTAMP
        WHERE column_id = ? AND position > ?
        """,
        (actual_column_id, old_position),
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
        "UPDATE card_placements SET position = -1, updated_at = CURRENT_TIMESTAMP WHERE card_id = ?",
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


def _validate_ai_operation(
    conn: sqlite3.Connection, board_id: int, operation: AIOperation
) -> None:
    if operation.type == "create_card":
        if not operation.column_id or not operation.title:
            raise ValidationError("create_card requires column_id and title")
        column_id = parse_api_id(operation.column_id, "col")
        _ensure_column_in_board(conn, board_id, column_id)
    elif operation.type == "update_card":
        if not operation.card_id:
            raise ValidationError("update_card requires card_id")
        card_id = parse_api_id(operation.card_id, "card")
        _ensure_card_in_board(conn, board_id, card_id)
    elif operation.type == "move_card":
        if not operation.card_id or not operation.column_id:
            raise ValidationError("move_card requires card_id and column_id")
        card_id = parse_api_id(operation.card_id, "card")
        target_column_id = parse_api_id(operation.column_id, "col")
        _ensure_column_in_board(conn, board_id, target_column_id)
        _ensure_card_in_board(conn, board_id, card_id)
    elif operation.type == "delete_card":
        if not operation.card_id:
            raise ValidationError("delete_card requires card_id")
        card_id = parse_api_id(operation.card_id, "card")
        _ensure_card_in_board(conn, board_id, card_id)
    elif operation.type == "rename_column":
        if not operation.column_id or not operation.title:
            raise ValidationError("rename_column requires column_id and title")
        column_id = parse_api_id(operation.column_id, "col")
        _ensure_column_in_board(conn, board_id, column_id)


def _apply_ai_operation(
    conn: sqlite3.Connection, board_id: int, operation: AIOperation
) -> None:
    if operation.type == "create_card":
        column_id = parse_api_id(operation.column_id or "", "col")
        _ensure_column_in_board(conn, board_id, column_id)
        max_pos = conn.execute(
            "SELECT COALESCE(MAX(position), -1) AS mp FROM card_placements WHERE column_id = ?",
            (column_id,),
        ).fetchone()["mp"]
        cursor = conn.execute(
            "INSERT INTO cards (board_id, title, details) VALUES (?, ?, ?)",
            (board_id, operation.title.strip(), (operation.details or "").strip()),
        )
        card_id = int(cursor.lastrowid)
        conn.execute(
            "INSERT INTO card_placements (card_id, column_id, position) VALUES (?, ?, ?)",
            (card_id, column_id, int(max_pos) + 1),
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
