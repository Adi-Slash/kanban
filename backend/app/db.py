import sqlite3
from contextlib import contextmanager
from pathlib import Path


DEFAULT_COLUMNS = [
    ("backlog", "Backlog"),
    ("discovery", "Discovery"),
    ("progress", "In Progress"),
    ("review", "Review"),
    ("done", "Done"),
]

DEFAULT_CARDS = [
    ("Align roadmap themes", "Draft quarterly themes with impact statements and metrics."),
    ("Gather customer signals", "Review support tags, sales notes, and churn feedback."),
    ("Prototype analytics view", "Sketch initial dashboard layout and key drill-downs."),
    ("Refine status language", "Standardize column labels and tone across the board."),
    ("Design card layout", "Add hierarchy and spacing for scanning dense lists."),
    ("QA micro-interactions", "Verify hover, focus, and loading states."),
    ("Ship marketing page", "Final copy approved and asset pack delivered."),
    ("Close onboarding sprint", "Document release notes and share internally."),
]

DEFAULT_PLACEMENTS = {
    0: [0, 1],  # backlog
    1: [2],  # discovery
    2: [3, 4],  # in progress
    3: [5],  # review
    4: [6, 7],  # done
}


SCHEMA_SQL = """
PRAGMA foreign_keys = ON;

CREATE TABLE IF NOT EXISTS users (
  id INTEGER PRIMARY KEY AUTOINCREMENT,
  username TEXT NOT NULL UNIQUE,
  password TEXT NOT NULL,
  created_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP
);

CREATE TABLE IF NOT EXISTS boards (
  id INTEGER PRIMARY KEY AUTOINCREMENT,
  user_id INTEGER NOT NULL UNIQUE,
  name TEXT NOT NULL DEFAULT 'My Board',
  created_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP,
  updated_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP,
  FOREIGN KEY (user_id) REFERENCES users(id) ON DELETE CASCADE
);

CREATE TABLE IF NOT EXISTS columns (
  id INTEGER PRIMARY KEY AUTOINCREMENT,
  board_id INTEGER NOT NULL,
  slug TEXT NOT NULL,
  title TEXT NOT NULL,
  position INTEGER NOT NULL,
  created_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP,
  updated_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP,
  FOREIGN KEY (board_id) REFERENCES boards(id) ON DELETE CASCADE,
  UNIQUE (board_id, slug),
  UNIQUE (board_id, position)
);

CREATE TABLE IF NOT EXISTS cards (
  id INTEGER PRIMARY KEY AUTOINCREMENT,
  board_id INTEGER NOT NULL,
  title TEXT NOT NULL,
  details TEXT NOT NULL DEFAULT '',
  created_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP,
  updated_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP,
  FOREIGN KEY (board_id) REFERENCES boards(id) ON DELETE CASCADE
);

CREATE TABLE IF NOT EXISTS card_placements (
  card_id INTEGER PRIMARY KEY,
  column_id INTEGER NOT NULL,
  position INTEGER NOT NULL,
  updated_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP,
  FOREIGN KEY (card_id) REFERENCES cards(id) ON DELETE CASCADE,
  FOREIGN KEY (column_id) REFERENCES columns(id) ON DELETE CASCADE,
  UNIQUE (column_id, position)
);

CREATE INDEX IF NOT EXISTS idx_columns_board_position ON columns(board_id, position);
CREATE INDEX IF NOT EXISTS idx_cards_board ON cards(board_id);
CREATE INDEX IF NOT EXISTS idx_card_placements_column_position ON card_placements(column_id, position);
"""


def to_column_api_id(db_id: int) -> str:
    return f"col-{db_id}"


def to_card_api_id(db_id: int) -> str:
    return f"card-{db_id}"


def parse_api_id(value: str, prefix: str) -> int:
    if not value.startswith(f"{prefix}-"):
        raise ValueError(f"Invalid {prefix} id")
    suffix = value[len(prefix) + 1 :]
    if not suffix.isdigit():
        raise ValueError(f"Invalid {prefix} id")
    return int(suffix)


@contextmanager
def sqlite_connection(db_path: Path):
    db_path.parent.mkdir(parents=True, exist_ok=True)
    conn = sqlite3.connect(db_path)
    conn.row_factory = sqlite3.Row
    conn.execute("PRAGMA foreign_keys = ON")
    try:
        yield conn
    finally:
        conn.close()


def initialize_database(db_path: Path) -> None:
    with sqlite_connection(db_path) as conn:
        conn.executescript(SCHEMA_SQL)
        _seed_default_user_board(conn)
        conn.commit()


def _seed_default_user_board(conn: sqlite3.Connection) -> None:
    existing = conn.execute(
        "SELECT id FROM users WHERE username = ?",
        ("user",),
    ).fetchone()
    if existing:
        return

    cursor = conn.execute(
        "INSERT INTO users (username, password) VALUES (?, ?)",
        ("user", "password"),
    )
    user_id = cursor.lastrowid
    cursor = conn.execute(
        "INSERT INTO boards (user_id, name) VALUES (?, ?)",
        (user_id, "My Board"),
    )
    board_id = cursor.lastrowid

    column_ids: list[int] = []
    for position, (slug, title) in enumerate(DEFAULT_COLUMNS):
        cursor = conn.execute(
            "INSERT INTO columns (board_id, slug, title, position) VALUES (?, ?, ?, ?)",
            (board_id, slug, title, position),
        )
        column_ids.append(int(cursor.lastrowid))

    card_ids: list[int] = []
    for title, details in DEFAULT_CARDS:
        cursor = conn.execute(
            "INSERT INTO cards (board_id, title, details) VALUES (?, ?, ?)",
            (board_id, title, details),
        )
        card_ids.append(int(cursor.lastrowid))

    for col_idx, card_indexes in DEFAULT_PLACEMENTS.items():
        column_id = column_ids[col_idx]
        for position, card_index in enumerate(card_indexes):
            conn.execute(
                "INSERT INTO card_placements (card_id, column_id, position) VALUES (?, ?, ?)",
                (card_ids[card_index], column_id, position),
            )
