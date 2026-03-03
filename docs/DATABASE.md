# Database Schema (v2)

SQLite database with normalized tables. Schema version tracked via `PRAGMA user_version`.

## Tables

### users
| Column | Type | Notes |
|--------|------|-------|
| id | INTEGER PK | Auto-increment |
| username | TEXT UNIQUE | Login identifier |
| display_name | TEXT | User's display name |
| password_hash | TEXT | PBKDF2-SHA256 with salt |
| created_at | TEXT | Timestamp |

### boards
| Column | Type | Notes |
|--------|------|-------|
| id | INTEGER PK | Auto-increment |
| user_id | INTEGER FK | References users(id), CASCADE delete |
| name | TEXT | Board name |
| description | TEXT | Board description |
| created_at | TEXT | Timestamp |
| updated_at | TEXT | Timestamp |

Multiple boards per user are supported.

### columns
| Column | Type | Notes |
|--------|------|-------|
| id | INTEGER PK | Auto-increment |
| board_id | INTEGER FK | References boards(id), CASCADE delete |
| slug | TEXT | Unique per board |
| title | TEXT | Display title |
| position | INTEGER | Sort order, unique per board |
| created_at | TEXT | Timestamp |
| updated_at | TEXT | Timestamp |

### cards
| Column | Type | Notes |
|--------|------|-------|
| id | INTEGER PK | Auto-increment |
| board_id | INTEGER FK | References boards(id), CASCADE delete |
| title | TEXT | Card title |
| details | TEXT | Card description |
| priority | TEXT | low/medium/high/urgent |
| due_date | TEXT | ISO date string, nullable |
| created_at | TEXT | Timestamp |
| updated_at | TEXT | Timestamp |

### card_placements
| Column | Type | Notes |
|--------|------|-------|
| card_id | INTEGER PK FK | References cards(id), CASCADE delete |
| column_id | INTEGER FK | References columns(id), CASCADE delete |
| position | INTEGER | Sort order, unique per column |
| updated_at | TEXT | Timestamp |

### labels
| Column | Type | Notes |
|--------|------|-------|
| id | INTEGER PK | Auto-increment |
| board_id | INTEGER FK | References boards(id), CASCADE delete |
| name | TEXT | Label name, unique per board |
| color | TEXT | Hex color code |
| created_at | TEXT | Timestamp |

### card_labels
| Column | Type | Notes |
|--------|------|-------|
| card_id | INTEGER PK FK | References cards(id), CASCADE delete |
| label_id | INTEGER PK FK | References labels(id), CASCADE delete |

## API ID Mapping

Internal integer IDs are mapped to string API IDs:
- Boards: `board-{id}`
- Columns: `col-{id}`
- Cards: `card-{id}`
- Labels: `label-{id}`

## Seed Data

On first initialization, the database is seeded with:
- Default user: `user` / `password` (hashed)
- One board with 5 columns and 8 cards
- 5 default labels (Bug, Feature, Enhancement, Documentation, Design)

## Migration

Schema version is tracked in `PRAGMA user_version`. When the schema version increases, all tables are dropped and recreated. This is acceptable for the development phase.
