def test_board_has_seed_labels(auth_client, board_id) -> None:
    board = auth_client.get(f"/api/boards/{board_id}").json()
    assert len(board["labels"]) == 5
    names = {l["name"] for l in board["labels"]}
    assert "Bug" in names
    assert "Feature" in names


def test_create_label(auth_client, board_id) -> None:
    response = auth_client.post(
        f"/api/boards/{board_id}/labels",
        json={"name": "Hotfix", "color": "#ff5500"},
    )
    assert response.status_code == 201
    data = response.json()
    assert data["name"] == "Hotfix"
    assert data["color"] == "#ff5500"
    assert data["id"].startswith("label-")


def test_create_duplicate_label(auth_client, board_id) -> None:
    response = auth_client.post(
        f"/api/boards/{board_id}/labels",
        json={"name": "Bug", "color": "#ff0000"},
    )
    assert response.status_code == 409


def test_update_label(auth_client, board_id) -> None:
    board = auth_client.get(f"/api/boards/{board_id}").json()
    label_id = board["labels"][0]["id"]

    response = auth_client.patch(
        f"/api/boards/{board_id}/labels/{label_id}",
        json={"name": "Critical Bug", "color": "#cc0000"},
    )
    assert response.status_code == 200
    assert response.json()["name"] == "Critical Bug"
    assert response.json()["color"] == "#cc0000"


def test_delete_label(auth_client, board_id) -> None:
    create = auth_client.post(
        f"/api/boards/{board_id}/labels",
        json={"name": "Temp Label", "color": "#aaaaaa"},
    )
    label_id = create.json()["id"]

    response = auth_client.delete(f"/api/boards/{board_id}/labels/{label_id}")
    assert response.status_code == 204

    board = auth_client.get(f"/api/boards/{board_id}").json()
    assert not any(l["id"] == label_id for l in board["labels"])


def test_set_card_labels(auth_client, board_id) -> None:
    board = auth_client.get(f"/api/boards/{board_id}").json()
    card_id = board["columns"][0]["cardIds"][0]
    label_ids = [board["labels"][0]["id"], board["labels"][1]["id"]]

    response = auth_client.put(
        f"/api/boards/{board_id}/cards/{card_id}/labels",
        json={"labelIds": label_ids},
    )
    assert response.status_code == 200
    updated_card = response.json()["cards"][card_id]
    assert set(updated_card["labelIds"]) == set(label_ids)


def test_clear_card_labels(auth_client, board_id) -> None:
    board = auth_client.get(f"/api/boards/{board_id}").json()
    card_id = board["columns"][0]["cardIds"][0]
    label_id = board["labels"][0]["id"]

    auth_client.put(
        f"/api/boards/{board_id}/cards/{card_id}/labels",
        json={"labelIds": [label_id]},
    )

    response = auth_client.put(
        f"/api/boards/{board_id}/cards/{card_id}/labels",
        json={"labelIds": []},
    )
    assert response.status_code == 200
    assert response.json()["cards"][card_id]["labelIds"] == []


def test_delete_label_removes_from_cards(auth_client, board_id) -> None:
    board = auth_client.get(f"/api/boards/{board_id}").json()
    card_id = board["columns"][0]["cardIds"][0]
    label_id = board["labels"][0]["id"]

    auth_client.put(
        f"/api/boards/{board_id}/cards/{card_id}/labels",
        json={"labelIds": [label_id]},
    )

    auth_client.delete(f"/api/boards/{board_id}/labels/{label_id}")

    board = auth_client.get(f"/api/boards/{board_id}").json()
    assert label_id not in board["cards"][card_id]["labelIds"]
