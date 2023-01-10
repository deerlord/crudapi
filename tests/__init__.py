import os
from typing import Generator, Tuple

import pytest
from httpx import AsyncClient

from crudapi import setup_application


@pytest.fixture
def setup() -> Generator[Tuple[setup_application, AsyncClient], None, None]:
    os.environ["DEBUG"] = "TRUE"
    os.environ["API_HOST"] = "localhost"
    os.environ["API_PORT"] = "8000"
    app = setup_application()
    yield app, AsyncClient(app=app, base_url="http://localhost:8000")
    if os.path.exists("./data.sqlite"):
        os.remove("./data.sqlite")
