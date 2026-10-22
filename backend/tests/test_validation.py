async def test_register_requires_privacy_consent(client) -> None:
    response = await client.post(
        "/api/v1/auth/register",
        json={
            "email": "test@example.com",
            "password": "password123",
            "privacy_accepted": False,
        },
    )
    assert response.status_code == 422
    body = response.json()
    assert body["code"] == "validation_error"


async def test_register_rejects_bad_username(client) -> None:
    response = await client.post(
        "/api/v1/auth/register",
        json={
            "email": "test@example.com",
            "password": "password123",
            "username": "a b c",
            "privacy_accepted": True,
        },
    )
    assert response.status_code == 422


async def test_protected_route_requires_token(client) -> None:
    response = await client.get("/api/v1/cases")
    assert response.status_code == 401
    assert response.json()["code"] == "missing_token"


async def test_logout_requires_token(client) -> None:
    response = await client.post("/api/v1/auth/logout")
    assert response.status_code == 401
    assert response.json()["code"] == "missing_token"


async def test_admin_route_requires_token(client) -> None:
    response = await client.get("/api/v1/admin/counselors")
    assert response.status_code == 401
