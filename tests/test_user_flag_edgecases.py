##################################################################################################
#                                            OVERVIEW                                            #
#                                                                                                #
# Tests edge cases of src.user_flag module.                                                      #
# Covers retry logic, error handling, and graceful fallback for translation and scoring steps.   #
# Ensures _post_json_with_retry and _process_row behave predictably under failure conditions.    #
##################################################################################################

##################################################################################################
#                                            IMPORTS                                             #
##################################################################################################

import asyncio

import httpx
import pytest

from src.user_flag import _post_json_with_retry, _process_row

##################################################################################################
#                                             TESTS                                              #
##################################################################################################

pytestmark = pytest.mark.asyncio


async def test_post_json_with_retry_success(mocker):
    """
    Validate normal POST request flow returning JSON.
    """
    fake_resp = mocker.AsyncMock()
    fake_resp.status_code = 200
    fake_resp.json = mocker.AsyncMock(return_value={"ok": True})  # debe ser AsyncMock
    mock_post = mocker.AsyncMock(return_value=fake_resp)

    client = mocker.Mock(post=mock_post)
    result = await _post_json_with_retry(client, "url", {"a": 1}, timeout_s=0.1, retries=0)
    assert result == {"ok": True}
    mock_post.assert_called_once()


async def test_post_json_with_retry_retry_and_fail(mocker):
    """
    Simulate retry logic for retryable HTTP status codes (500, 503).
    """
    fake_resp = mocker.AsyncMock()
    fake_resp.status_code = 500
    fake_resp.request = mocker.Mock()
    fake_resp.response = fake_resp
    mocker.patch("asyncio.sleep", return_value=None)
    client = mocker.Mock(post=mocker.AsyncMock(return_value=fake_resp))

    with pytest.raises(httpx.HTTPStatusError):
        await _post_json_with_retry(client, "url", {"a": 1}, timeout_s=0.1, retries=1)


async def test_process_row_translation_empty(monkeypatch):
    """
    Ensure _process_row handles empty translation gracefully and returns score 0.0.
    """

    async def fake_post(*_, **__):
        return {"text_en": ""}

    monkeypatch.setattr("src.user_flag._post_json_with_retry", fake_post)
    client = object()
    result = await _process_row(
        sem=asyncio.Semaphore(1),
        client=client,
        translation_url="t",
        scoring_url="s",
        timeout_s=0.1,
        retries=0,
        user_id="u1",
        message="msg",
    )
    assert result == ("u1", 0.0)


async def test_process_row_raises_exception(monkeypatch):
    """
    Verify _process_row catches exceptions and returns (user_id, 0.0).
    """

    async def bad_post(*_, **__):
        raise httpx.RequestError("fail")

    monkeypatch.setattr("src.user_flag._post_json_with_retry", bad_post)
    client = object()
    result = await _process_row(
        sem=asyncio.Semaphore(1),
        client=client,
        translation_url="t",
        scoring_url="s",
        timeout_s=0.1,
        retries=0,
        user_id="u2",
        message="oops",
    )
    assert result == ("u2", 0.0)
