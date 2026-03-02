def test_get_board_returns_seeded_data(client) -> None:
    response = client.get("/api/board")
    assert response.status_code == 200

    payload = response.json()
    assert len(payload["columns"]) == 5
    assert payload["columns"][0]["title"] == "Backlog"


def test_rename_column_endpoint(client) -> None:
    board = client.get("/api/board").json()
    column_id = board["columns"][0]["id"]

    response = client.patch(f"/api/columns/{column_id}", json={"title": "New Backlog"})
    assert response.status_code == 200
    assert response.json()["columns"][0]["title"] == "New Backlog"


def test_add_and_delete_card_endpoints(client) -> None:
    board = client.get("/api/board").json()
    column_id = board["columns"][0]["id"]

    create_response = client.post(
        f"/api/columns/{column_id}/cards",
        json={"title": "API Card", "details": "Created through API"},
    )
    assert create_response.status_code == 200
    created_board = create_response.json()
    created_card_id = created_board["columns"][0]["cardIds"][-1]

    delete_response = client.delete(f"/api/columns/{column_id}/cards/{created_card_id}")
    assert delete_response.status_code == 200
    assert created_card_id not in delete_response.json()["cards"]


def test_move_card_endpoint(client) -> None:
    board = client.get("/api/board").json()
    card_id = board["columns"][0]["cardIds"][0]
    target_column_id = board["columns"][3]["id"]

    response = client.post(
        f"/api/cards/{card_id}/move",
        json={"targetColumnId": target_column_id},
    )
    assert response.status_code == 200
    assert card_id in response.json()["columns"][3]["cardIds"]


def test_invalid_card_id_returns_422(client) -> None:
    response = client.post(
        "/api/cards/not-a-valid-id/move",
        json={"targetColumnId": "col-1"},
    )
    assert response.status_code == 422


def test_board_changes_persist_across_requests(client) -> None:
    board = client.get("/api/board").json()
    first_column_id = board["columns"][0]["id"]
    review_column_id = next(
        column["id"] for column in board["columns"] if column["title"] == "Review"
    )

    add_response = client.post(
        f"/api/columns/{first_column_id}/cards",
        json={"title": "Persistence check card", "details": "Persists across requests"},
    )
    assert add_response.status_code == 200
    created_card_id = add_response.json()["columns"][0]["cardIds"][-1]

    after_add = client.get("/api/board").json()
    assert created_card_id in after_add["cards"]

    move_response = client.post(
        f"/api/cards/{created_card_id}/move",
        json={"targetColumnId": review_column_id},
    )
    assert move_response.status_code == 200

    after_move = client.get("/api/board").json()
    review_column = next(
        column for column in after_move["columns"] if column["id"] == review_column_id
    )
    assert created_card_id in review_column["cardIds"]
