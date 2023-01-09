import pytest

from tests import setup  # type: ignore


@pytest.mark.asyncio
async def test_health_success(setup):
    _, client = setup
    response = await client.get("/health")
    assert response.status_code == 200
