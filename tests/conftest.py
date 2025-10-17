##################################################################################################
#                                            OVERVIEW                                            #
#                                                                                                #
# Provides pytest fixtures for async FastAPI testing.                                            #
# - anyio_backend: forces asyncio backend for pytest-anyio.                                      #
# - test_client  : Async HTTPX client bound to the ASGI app using ASGITransport.                 #
##################################################################################################

##################################################################################################
#                                            IMPORTS                                             #
##################################################################################################

from collections.abc import AsyncGenerator

import httpx
import pytest
from httpx import AsyncClient

from app import app

##################################################################################################
#                                             TESTS                                              #
##################################################################################################


@pytest.fixture
def anyio_backend() -> str:
    """
    Force pytest-anyio to use the asyncio backend.
    This avoids backend conflicts when running async tests.
    """
    return "asyncio"


@pytest.fixture
async def test_client() -> AsyncGenerator[AsyncClient, None]:
    """
    Provides an HTTPX AsyncClient bound to the FastAPI ASGI app.
    Allows sending HTTP requests to the app during tests.
    """
    async with httpx.AsyncClient(transport=httpx.ASGITransport(app=app), base_url="http://test") as client:
        # Yield ensures proper cleanup of the async context after each test
        yield client
