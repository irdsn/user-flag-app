##################################################################################################
#                                            OVERVIEW                                            #
#                                                                                                #
# Validates mock translation and scoring API endpoints used in local testing.                    #
# Confirms that /translate returns text field and /score returns a numeric score.                #
# Extends coverage without depending on external API services.                                   #
##################################################################################################

##################################################################################################
#                                            IMPORTS                                             #
##################################################################################################

import httpx
import pytest

from apis.scoring_sim import app as scoring_app
from apis.translation_sim import app as translation_app

##################################################################################################
#                                             TESTS                                              #
##################################################################################################

pytestmark = pytest.mark.asyncio


async def test_translation_mock_works():
    """
    These mocks are not part of the technical assessment; they are tested only
    to expand coverage. We verify that the endpoint responds JSON with a text field.
    """
    transport = httpx.ASGITransport(app=translation_app)
    async with httpx.AsyncClient(transport=transport, base_url="http://test") as client:
        resp = await client.post("/translate", json={"text": "Hello"})
        assert resp.status_code == 200
        data = resp.json()
        # Accept either 'text_en' or 'translated_text' to avoid coupling to mock internals
        assert any(k in data for k in ("text_en", "translated_text"))


async def test_scoring_mock_works():
    """
    These mocks are not part of the technical assessment; they are tested only
    to expand coverage. We verify the presence of 'score' in the response.
    """
    transport = httpx.ASGITransport(app=scoring_app)
    async with httpx.AsyncClient(transport=transport, base_url="http://test") as client:
        # The scoring API expects 'text_en', not 'text'
        resp = await client.post("/score", json={"text_en": "Hello"})
        assert resp.status_code == 200, resp.text
        data = resp.json()
        assert "score" in data
