# Database Design (Phase 5)

This document proposes the normalized SQLite schema for the MVP Kanban app and the approach to produce board JSON for UI and AI usage.

## Goals

- Keep schema normalized and simple.
- Support one board per signed-in user in MVP, while allowing multiple users and future expansion.
- Preserve ordering for columns and cards.
- Make it easy to construct and persist board JSON snapshots from relational data.

## SQLite Schema

```sql
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
```

## Why this schema

- `users` supports future multi-user behavior.
- `boards.user_id UNIQUE` enforces one board per user for MVP.
- `columns.position` and `card_placements.position` preserve deterministic ordering.
- `cards` is independent from placement, so moving a card only updates placement data.
- `card_placements.card_id PRIMARY KEY` guarantees each card is in exactly one column.

## Board JSON projection strategy

The frontend and AI flows need the board in a JSON shape similar to the existing frontend model. Build that from relational rows:

1. Load board for user.
2. Load ordered columns (`ORDER BY position`).
3. Load cards joined with placement and ordered by `(column.position, card_placements.position)`.
4. Construct JSON:
   - `columns[]`: each with `id`, `title`, and ordered `cardIds[]`
   - `cards{}`: map of card id to card payload

Example response shape:

```json
{
  "columns": [
    { "id": "col-1", "title": "Backlog", "cardIds": ["card-1", "card-2"] }
  ],
  "cards": {
    "card-1": { "id": "card-1", "title": "Task A", "details": "..." }
  }
}
```

Implementation note: database integer IDs can be translated to frontend IDs (`col-{id}`, `card-{id}`) at the API boundary to preserve current client expectations.

## Write/update strategy

- Wrap all board mutations in one transaction.
- For reorder/move operations:
  - Update affected `position` values in minimal ranges.
  - Update `updated_at` on changed rows.
- For delete operations:
  - Delete from `cards`; placement is removed by cascade.

## Bootstrap and migration approach

- On backend startup:
  - Create DB file if missing.
  - Execute `CREATE TABLE IF NOT EXISTS` statements.
  - Ensure required indexes exist.
- Seed default data for MVP user on first run:
  - user: `user` / `password`
  - one board for that user
  - five default columns
  - starter cards (optional if keeping empty board)

## Test plan

- Schema bootstrap test:
  - Fresh DB creates all tables/indexes without error.
- Relational integrity test:
  - Invalid foreign keys fail.
  - Card cannot exist in multiple columns (placement PK).
- Ordering test:
  - Reordering columns/cards persists and round-trips correctly.
- Projection test:
  - Relational data converts to expected board JSON shape/order.
- Transaction safety test:
  - Partial failure in multi-step update rolls back all changes.

## Open decisions for sign-off

- ID strategy:
  - Keep integer DB IDs internally and map to `col-*` / `card-*` in API (recommended), or
  - Store string IDs directly in DB.
- Seed policy:
  - Seed starter cards, or seed only empty columns.

## Recommendation

- Use integer IDs in DB with API mapping to string IDs.
- Seed default columns plus starter cards to match current demo behavior.
