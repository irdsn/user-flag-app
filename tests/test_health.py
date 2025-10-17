##################################################################################################
#                                            OVERVIEW                                            #
#                                                                                                #
# Basic async test for the /health endpoint.                                                     #
# Verifies HTTP 200 response and checks that 'status' field is one of {ok, healthy, alive}.      #
##################################################################################################

##################################################################################################
#                                            IMPORTS                                             #
##################################################################################################

import pytest

##################################################################################################
#                                             TESTS                                              #
##################################################################################################

pytestmark = pytest.mark.asyncio


async def test_health_endpoint(test_client):
    """Ensure the /health endpoint returns HTTP 200."""
    resp = await test_client.get("/health")
    assert resp.status_code == 200
    data = resp.json()
    assert data.get("status") in {"ok", "healthy", "alive"}
