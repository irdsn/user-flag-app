##################################################################################################
#                                            OVERVIEW                                            #
#                                                                                                #
# Tests edge cases of FastAPI app endpoints (app.py).                                            #
# Covers missing metrics, invalid input path, and pipeline failure exceptions.                   #
##################################################################################################

##################################################################################################
#                                            IMPORTS                                             #
##################################################################################################

import importlib.util
import pathlib
import sys
import pytest
import os
import types
import asyncio
import httpx
from src import user_flag
from src.user_flag import _post_json_with_retry

##################################################################################################
#                                             TESTS                                              #
##################################################################################################

pytestmark = pytest.mark.asyncio

async def test_metrics_before_any_run(test_client):
    """No pipeline executed yet → returns default message."""
    resp = await test_client.get("/metrics")
    assert resp.status_code == 200
    data = resp.json()
    assert "No pipeline" in data["message"]


async def test_run_with_nonexistent_file(tmp_path, test_client):
    """Non-existent input file → returns error JSON."""
    bogus_file = tmp_path / "missing.csv"
    payload = {"input_file_path": str(bogus_file)}
    resp = await test_client.post("/run", json=payload)
    assert resp.status_code == 200
    data = resp.json()
    assert "error" in data
    assert "not found" in data["error"]


async def test_run_pipeline_exception(monkeypatch, tmp_path, test_client):
    """Simulate internal exception during run_pipeline execution."""
    dummy_input = tmp_path / "input.csv"
    dummy_input.write_text("user_id,message\n1,Hi\n", encoding="utf-8")

    # Force run_pipeline to raise an exception
    monkeypatch.setattr("app.run_pipeline", lambda *a, **kw: (_ for _ in ()).throw(Exception("boom")))

    payload = {"input_file_path": str(dummy_input)}
    resp = await test_client.post("/run", json=payload)
    assert resp.status_code == 200
    data = resp.json()
    assert "error" in data and "boom" in data["error"]


def test_env_float_invalid(monkeypatch):
    """Invalid float in environment → returns default value."""
    monkeypatch.setattr(os, "getenv", lambda *_: "abc")
    assert user_flag._env_float("X", 3.14) == 3.14


def test_env_int_invalid(monkeypatch):
    """Invalid int in environment → returns default value."""
    monkeypatch.setattr(os, "getenv", lambda *_: "abc")
    assert user_flag._env_int("Y", 42) == 42


@pytest.mark.asyncio
async def test_post_json_with_retry_request_none(mocker):
    """
    Validate that a response without 'request' attribute triggers a RequestError.
    """
    fake_resp = mocker.AsyncMock()
    fake_resp.status_code = 400

    # Explicitly remove the 'request' attribute if it exists
    if hasattr(fake_resp, "request"):
        del fake_resp.request

    client = mocker.Mock(post=mocker.AsyncMock(return_value=fake_resp))

    # Expect RequestError raised due to missing 'request' in response
    with pytest.raises(httpx.RequestError, match="Missing request"):
        await _post_json_with_retry(client, "url", {}, timeout_s=0.1, retries=0)




@pytest.mark.asyncio
async def test_post_json_with_retry_all_attempts_fail(mocker):
    """All retries exhausted → raises final exception and logs error."""
    fake_resp = mocker.AsyncMock(status_code=500)
    fake_resp.request = mocker.Mock()
    fake_resp.response = fake_resp
    client = mocker.Mock(post=mocker.AsyncMock(return_value=fake_resp))
    mocker.patch("asyncio.sleep", return_value=None)

    with pytest.raises(httpx.HTTPStatusError):
        await user_flag._post_json_with_retry(client, "url", {}, timeout_s=0.01, retries=1)


def test_main_entrypoint(monkeypatch):
    """
    Simulate execution of src.user_flag.py as a CLI (__main__ context).
    Ensures asyncio.run is invoked and the pipeline executes successfully.
    """
    called = {}

    def fake_run(*_, **__):
        called["executed"] = True
        return {"users": 1, "rows_processed": 1}

    # Create fake asyncio module including both Semaphore and our fake run
    fake_asyncio = types.SimpleNamespace(
        run=fake_run,
        Semaphore=asyncio.Semaphore,
        iscoroutine=asyncio.iscoroutine,
        as_completed=asyncio.as_completed,
        create_task=asyncio.create_task,
        sleep=asyncio.sleep,
    )

    fake_time = types.SimpleNamespace(perf_counter=lambda: 0)

    monkeypatch.setitem(sys.modules, "asyncio", fake_asyncio)
    monkeypatch.setitem(sys.modules, "time", fake_time)

    # Load src/user_flag.py as __main__
    module_path = pathlib.Path("src/user_flag.py").resolve()
    spec = importlib.util.spec_from_file_location("__main__", module_path)
    mod = importlib.util.module_from_spec(spec)
    sys.modules["__main__"] = mod
    spec.loader.exec_module(mod)

    assert called.get("executed") is True


