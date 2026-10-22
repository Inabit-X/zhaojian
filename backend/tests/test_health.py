async def test_live(client) -> None:
    response = await client.get("/api/v1/health/live")
    assert response.status_code == 200
    assert response.json() == {"status": "ok"}


async def test_root_disclaimer(client) -> None:
    response = await client.get("/")
    assert response.status_code == 200
    assert "非医疗产品" in response.json()["disclaimer"]
