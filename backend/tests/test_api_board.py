def test_get_board_returns_seeded_data(auth_client, board_id) -> None:
    response = auth_client.get(f"/api/boards/{board_id}")
    assert response.status_code == 200

    payload = response.json()
    assert payload["id"] == board_id
    assert payload["name"] == "My Board"
    assert len(payload["columns"]) == 5
    assert payload["columns"][0]["title"] == "Backlog"
    assert len(payload["labels"]) == 5


def test_list_boards(auth_client) -> None:
    response = auth_client.get("/api/boards")
    assert response.status_code == 200
    boards = response.json()
    assert len(boards) >= 1
    assert boards[0]["name"] == "My Board"
    assert boards[0]["columnCount"] == 5
    assert boards[0]["cardCount"] == 8


def test_create_board(auth_client) -> None:
    response = auth_client.post(
        "/api/boards",
        json={"name": "Sprint Board", "description": "For sprint planning"},
    )
    assert response.status_code == 201
    data = response.json()
    assert data["name"] == "Sprint Board"
    assert data["description"] == "For sprint planning"
    assert data["columnCount"] == 5
    assert data["cardCount"] == 0

    boards = auth_client.get("/api/boards").json()
    assert len(boards) == 2


def test_update_board(auth_client, board_id) -> None:
    response = auth_client.patch(
        f"/api/boards/{board_id}",
        json={"name": "Renamed Board", "description": "Updated desc"},
    )
    assert response.status_code == 200
    assert response.json()["name"] == "Renamed Board"
    assert response.json()["description"] == "Updated desc"


def test_delete_board(auth_client) -> None:
    create = auth_client.post(
        "/api/boards", json={"name": "Temp Board"}
    )
    temp_id = create.json()["id"]

    delete = auth_client.delete(f"/api/boards/{temp_id}")
    assert delete.status_code == 204

    boards = auth_client.get("/api/boards").json()
    assert not any(b["id"] == temp_id for b in boards)


def test_get_nonexistent_board(auth_client) -> None:
    response = auth_client.get("/api/boards/board-99999")
    assert response.status_code == 404


def test_rename_column_endpoint(auth_client, board_id) -> None:
    board = auth_client.get(f"/api/boards/{board_id}").json()
    column_id = board["columns"][0]["id"]

    response = auth_client.patch(
        f"/api/boards/{board_id}/columns/{column_id}",
        json={"title": "New Backlog"},
    )
    assert response.status_code == 200
    assert response.json()["columns"][0]["title"] == "New Backlog"


def test_add_and_delete_card_endpoints(auth_client, board_id) -> None:
    board = auth_client.get(f"/api/boards/{board_id}").json()
    column_id = board["columns"][0]["id"]

    create_response = auth_client.post(
        f"/api/boards/{board_id}/columns/{column_id}/cards",
        json={"title": "API Card", "details": "Created through API", "priority": "high"},
    )
    assert create_response.status_code == 200
    created_board = create_response.json()
    created_card_id = created_board["columns"][0]["cardIds"][-1]
    assert created_board["cards"][created_card_id]["priority"] == "high"

    delete_response = auth_client.delete(
        f"/api/boards/{board_id}/columns/{column_id}/cards/{created_card_id}"
    )
    assert delete_response.status_code == 200
    assert created_card_id not in delete_response.json()["cards"]


def test_update_card(auth_client, board_id) -> None:
    board = auth_client.get(f"/api/boards/{board_id}").json()
    card_id = board["columns"][0]["cardIds"][0]

    response = auth_client.patch(
        f"/api/boards/{board_id}/cards/{card_id}",
        json={"title": "Updated Title", "priority": "urgent", "dueDate": "2026-12-31"},
    )
    assert response.status_code == 200
    updated_card = response.json()["cards"][card_id]
    assert updated_card["title"] == "Updated Title"
    assert updated_card["priority"] == "urgent"
    assert updated_card["dueDate"] == "2026-12-31"


def test_clear_due_date(auth_client, board_id) -> None:
    board = auth_client.get(f"/api/boards/{board_id}").json()
    card_id = board["columns"][0]["cardIds"][0]

    auth_client.patch(
        f"/api/boards/{board_id}/cards/{card_id}",
        json={"dueDate": "2026-06-15"},
    )

    response = auth_client.patch(
        f"/api/boards/{board_id}/cards/{card_id}",
        json={"dueDate": None},
    )
    assert response.status_code == 200
    assert response.json()["cards"][card_id]["dueDate"] is None


def test_move_card_endpoint(auth_client, board_id) -> None:
    board = auth_client.get(f"/api/boards/{board_id}").json()
    card_id = board["columns"][0]["cardIds"][0]
    target_column_id = board["columns"][3]["id"]

    response = auth_client.post(
        f"/api/boards/{board_id}/cards/{card_id}/move",
        json={"targetColumnId": target_column_id},
    )
    assert response.status_code == 200
    assert card_id in response.json()["columns"][3]["cardIds"]


def test_invalid_card_id_returns_422(auth_client, board_id) -> None:
    response = auth_client.post(
        f"/api/boards/{board_id}/cards/not-a-valid-id/move",
        json={"targetColumnId": "col-1"},
    )
    assert response.status_code == 422


def test_board_changes_persist_across_requests(auth_client, board_id) -> None:
    board = auth_client.get(f"/api/boards/{board_id}").json()
    first_column_id = board["columns"][0]["id"]
    review_column_id = next(
        col["id"] for col in board["columns"] if col["title"] == "Review"
    )

    add = auth_client.post(
        f"/api/boards/{board_id}/columns/{first_column_id}/cards",
        json={"title": "Persistence check card", "details": "Persists"},
    )
    assert add.status_code == 200
    created_card_id = add.json()["columns"][0]["cardIds"][-1]

    after_add = auth_client.get(f"/api/boards/{board_id}").json()
    assert created_card_id in after_add["cards"]

    move = auth_client.post(
        f"/api/boards/{board_id}/cards/{created_card_id}/move",
        json={"targetColumnId": review_column_id},
    )
    assert move.status_code == 200

    after_move = auth_client.get(f"/api/boards/{board_id}").json()
    review_col = next(
        col for col in after_move["columns"] if col["id"] == review_column_id
    )
    assert created_card_id in review_col["cardIds"]


def test_board_isolation_between_users(client) -> None:
    client.post(
        "/api/auth/register",
        json={"username": "alice", "password": "pass1234"},
    )
    alice_boards = client.get("/api/boards").json()
    assert len(alice_boards) == 0

    client.post("/api/boards", json={"name": "Alice Board"})
    alice_boards = client.get("/api/boards").json()
    assert len(alice_boards) == 1

    client.post("/api/auth/logout")
    client.post(
        "/api/auth/login",
        json={"username": "user", "password": "password"},
    )
    user_boards = client.get("/api/boards").json()
    assert all(b["name"] != "Alice Board" for b in user_boards)
