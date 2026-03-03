def test_login_with_valid_credentials(client) -> None:
    response = client.post(
        "/api/auth/login",
        json={"username": "user", "password": "password"},
    )
    assert response.status_code == 200
    assert response.json()["message"] == "Login successful"
    assert "pm_session" in response.cookies


def test_login_with_invalid_credentials(client) -> None:
    response = client.post(
        "/api/auth/login",
        json={"username": "user", "password": "wrong"},
    )
    assert response.status_code == 401


def test_login_with_nonexistent_user(client) -> None:
    response = client.post(
        "/api/auth/login",
        json={"username": "nobody", "password": "password"},
    )
    assert response.status_code == 401


def test_register_new_user(client) -> None:
    response = client.post(
        "/api/auth/register",
        json={"username": "newuser", "password": "pass1234", "displayName": "New User"},
    )
    assert response.status_code == 200
    assert "pm_session" in response.cookies


def test_register_duplicate_username(client) -> None:
    response = client.post(
        "/api/auth/register",
        json={"username": "user", "password": "pass1234"},
    )
    assert response.status_code == 409


def test_register_then_login(client) -> None:
    client.post(
        "/api/auth/register",
        json={"username": "alice", "password": "alicepass"},
    )
    response = client.post(
        "/api/auth/login",
        json={"username": "alice", "password": "alicepass"},
    )
    assert response.status_code == 200


def test_auth_status_when_logged_in(auth_client) -> None:
    response = auth_client.get("/api/auth/status")
    assert response.status_code == 200
    assert response.json()["authenticated"] is True


def test_auth_status_when_not_logged_in(client) -> None:
    response = client.get("/api/auth/status")
    assert response.status_code == 200
    assert response.json()["authenticated"] is False


def test_logout(auth_client) -> None:
    response = auth_client.post("/api/auth/logout")
    assert response.status_code == 200

    status = auth_client.get("/api/auth/status")
    assert status.json()["authenticated"] is False


def test_protected_endpoint_without_auth(client) -> None:
    response = client.get("/api/boards")
    assert response.status_code == 401


def test_get_profile(auth_client) -> None:
    response = auth_client.get("/api/auth/profile")
    assert response.status_code == 200
    data = response.json()
    assert data["username"] == "user"
    assert data["displayName"] == "Demo User"


def test_update_profile(auth_client) -> None:
    response = auth_client.patch(
        "/api/auth/profile",
        json={"displayName": "Updated Name"},
    )
    assert response.status_code == 200
    assert response.json()["displayName"] == "Updated Name"

    profile = auth_client.get("/api/auth/profile").json()
    assert profile["displayName"] == "Updated Name"
