import hashlib
import secrets
import sqlite3
from contextlib import contextmanager
from pathlib import Path


SCHEMA_VERSION = 2

DEFAULT_COLUMNS = [
    ("backlog", "Backlog"),
    ("discovery", "Discovery"),
    ("progress", "In Progress"),
    ("review", "Review"),
    ("done", "Done"),
]

DEFAULT_CARDS = [
    ("Align roadmap themes", "Draft quarterly themes with impact statements and metrics.", "medium"),
    ("Gather customer signals", "Review support tags, sales notes, and churn feedback.", "high"),
    ("Prototype analytics view", "Sketch initial dashboard layout and key drill-downs.", "medium"),
    ("Refine status language", "Standardize column labels and tone across the board.", "low"),
    ("Design card layout", "Add hierarchy and spacing for scanning dense lists.", "medium"),
    ("QA micro-interactions", "Verify hover, focus, and loading states.", "high"),
    ("Ship marketing page", "Final copy approved and asset pack delivered.", "urgent"),
    ("Close onboarding sprint", "Document release notes and share internally.", "medium"),
]

DEFAULT_PLACEMENTS = {
    0: [0, 1],
    1: [2],
    2: [3, 4],
    3: [5],
    4: [6, 7],
}

DEFAULT_LABELS = [
    ("Bug", "#e74c3c"),
    ("Feature", "#209dd7"),
    ("Enhancement", "#753991"),
    ("Documentation", "#ecad0a"),
    ("Design", "#2ecc71"),
]

SCHEMA_SQL = """
PRAGMA foreign_keys = ON;

CREATE TABLE IF NOT EXISTS users (
  id INTEGER PRIMARY KEY AUTOINCREMENT,
  username TEXT NOT NULL UNIQUE,
  display_name TEXT NOT NULL DEFAULT '',
  password_hash TEXT NOT NULL,
  created_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP
);

CREATE TABLE IF NOT EXISTS boards (
  id INTEGER PRIMARY KEY AUTOINCREMENT,
  user_id INTEGER NOT NULL,
  name TEXT NOT NULL DEFAULT 'My Board',
  description TEXT NOT NULL DEFAULT '',
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
  priority TEXT NOT NULL DEFAULT 'medium',
  due_date TEXT,
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

CREATE TABLE IF NOT EXISTS labels (
  id INTEGER PRIMARY KEY AUTOINCREMENT,
  board_id INTEGER NOT NULL,
  name TEXT NOT NULL,
  color TEXT NOT NULL DEFAULT '#209dd7',
  created_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP,
  FOREIGN KEY (board_id) REFERENCES boards(id) ON DELETE CASCADE,
  UNIQUE (board_id, name)
);

CREATE TABLE IF NOT EXISTS card_labels (
  card_id INTEGER NOT NULL,
  label_id INTEGER NOT NULL,
  PRIMARY KEY (card_id, label_id),
  FOREIGN KEY (card_id) REFERENCES cards(id) ON DELETE CASCADE,
  FOREIGN KEY (label_id) REFERENCES labels(id) ON DELETE CASCADE
);

CREATE INDEX IF NOT EXISTS idx_boards_user ON boards(user_id);
CREATE INDEX IF NOT EXISTS idx_columns_board_position ON columns(board_id, position);
CREATE INDEX IF NOT EXISTS idx_cards_board ON cards(board_id);
CREATE INDEX IF NOT EXISTS idx_card_placements_column_position ON card_placements(column_id, position);
CREATE INDEX IF NOT EXISTS idx_labels_board ON labels(board_id);
"""


def hash_password(password: str) -> str:
    salt = secrets.token_hex(16)
    key = hashlib.pbkdf2_hmac("sha256", password.encode(), salt.encode(), 100_000)
    return f"{salt}:{key.hex()}"


def verify_password(password: str, stored_hash: str) -> bool:
    try:
        salt, key_hex = stored_hash.split(":", 1)
    except ValueError:
        return False
    key = hashlib.pbkdf2_hmac("sha256", password.encode(), salt.encode(), 100_000)
    return secrets.compare_digest(key.hex(), key_hex)


def to_column_api_id(db_id: int) -> str:
    return f"col-{db_id}"


def to_card_api_id(db_id: int) -> str:
    return f"card-{db_id}"


def to_board_api_id(db_id: int) -> str:
    return f"board-{db_id}"


def to_label_api_id(db_id: int) -> str:
    return f"label-{db_id}"


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
        version = conn.execute("PRAGMA user_version").fetchone()[0]
        if version < SCHEMA_VERSION:
            conn.executescript(
                "DROP TABLE IF EXISTS card_labels;"
                "DROP TABLE IF EXISTS labels;"
                "DROP TABLE IF EXISTS card_placements;"
                "DROP TABLE IF EXISTS cards;"
                "DROP TABLE IF EXISTS columns;"
                "DROP TABLE IF EXISTS boards;"
                "DROP TABLE IF EXISTS users;"
            )
            conn.executescript(SCHEMA_SQL)
            conn.execute(f"PRAGMA user_version = {SCHEMA_VERSION}")
            _seed_default_data(conn)
        conn.commit()


def _seed_default_data(conn: sqlite3.Connection) -> None:
    password_hash = hash_password("password")
    cursor = conn.execute(
        "INSERT INTO users (username, display_name, password_hash) VALUES (?, ?, ?)",
        ("user", "Demo User", password_hash),
    )
    user_id = cursor.lastrowid

    cursor = conn.execute(
        "INSERT INTO boards (user_id, name, description) VALUES (?, ?, ?)",
        (user_id, "My Board", "Default project board"),
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
    for title, details, priority in DEFAULT_CARDS:
        cursor = conn.execute(
            "INSERT INTO cards (board_id, title, details, priority) VALUES (?, ?, ?, ?)",
            (board_id, title, details, priority),
        )
        card_ids.append(int(cursor.lastrowid))

    for col_idx, card_indexes in DEFAULT_PLACEMENTS.items():
        column_id = column_ids[col_idx]
        for position, card_index in enumerate(card_indexes):
            conn.execute(
                "INSERT INTO card_placements (card_id, column_id, position) VALUES (?, ?, ?)",
                (card_ids[card_index], column_id, position),
            )

    for name, color in DEFAULT_LABELS:
        conn.execute(
            "INSERT INTO labels (board_id, name, color) VALUES (?, ?, ?)",
            (board_id, name, color),
        )
