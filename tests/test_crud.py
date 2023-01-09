import random

import pytest
from httpx import AsyncClient

from tests import setup  # type: ignore

ENDPOINT = "/crud/inventory/item"


@pytest.mark.asyncio
async def test_get_all_empty(setup):
    _, client = setup
    response = await client.get(ENDPOINT)
    assert response.status_code == 200
    assert response.json() == []


@pytest.mark.asyncio
async def test_get_all(setup):
    _, client = setup
    data = await make_several(client)
    response = await client.get(ENDPOINT)
    assert response.status_code == 200
    assert response.json() == data


@pytest.mark.asyncio
async def test_get_one_not_found(setup):
    _, client = setup
    response = await client.get(f"{ENDPOINT}/1")
    assert response.status_code == 404


@pytest.mark.asyncio
async def test_get_one(setup):
    _, client = setup
    data = await make_several(client)
    index = random.randrange(0, len(data))
    response = await client.get(f"{ENDPOINT}/{index+1}")
    assert response.status_code == 200
    assert data[index] == response.json()


@pytest.mark.asyncio
async def test_create(setup):
    _, client = setup
    expected_id = 1
    expected_name = "garlic"
    expected_model = {"id": expected_id, "name": expected_name}
    response = await client.post(ENDPOINT, json={"name": expected_name})
    assert response.status_code == 200
    assert response.json() == expected_model
    response = await client.get(ENDPOINT)
    assert response.status_code == 200
    assert response.json() == [expected_model]
    response = await client.get(f"{ENDPOINT}/{expected_id}")
    assert response.status_code == 200
    assert response.json() == expected_model


@pytest.mark.asyncio
async def test_create_many(setup):
    _, client = setup
    data = await make_several(client)
    item_id = random.randrange(1, len(data))
    response = await client.get(f"{ENDPOINT}/{item_id}")
    assert response.status_code == 200
    assert response.json() == data[item_id - 1]


@pytest.mark.asyncio
async def test_delete_one(setup):
    _, client = setup
    data = await make_several(client)
    item_id = random.randrange(1, len(data))
    response = await client.delete(f"{ENDPOINT}/{item_id}")
    expected_delete = data.pop(item_id - 1)
    assert response.status_code == 200
    assert response.json() == expected_delete
    response = await client.get(ENDPOINT)
    assert response.status_code == 200
    assert response.json() == data
    response = await client.get(f"{ENDPOINT}/{item_id}")
    assert response.status_code == 404


@pytest.mark.asyncio
async def test_delete_all(setup):
    _, client = setup
    await make_several(client)
    for method in (client.delete, client.get):
        response = await method(ENDPOINT)
        assert response.status_code == 200
        assert response.json() == []


@pytest.mark.asyncio
async def test_update(setup):
    _, client = setup
    data = await make_several(client)
    item = data[0]
    item_id = item["id"]
    response = await client.put(f"{ENDPOINT}/{item_id}", json={"name": "new"})
    assert response.status_code == 200
    json = response.json()
    assert json["name"] != item["name"]
    assert json["id"] == item_id


async def make_several(c: AsyncClient, count: int = 10) -> list:
    data = []
    for item_id in range(1, count):
        json = {"id": item_id, "name": f"name_{item_id}"}
        response = await c.post(ENDPOINT, json=json)
        assert response.status_code == 200
        assert response.json() == json
        data.append(json)
    response = await c.get(ENDPOINT)
    assert response.status_code == 200
    assert response.json() == data
    return data
