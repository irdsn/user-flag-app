##################################################################################################
#                                            OVERVIEW                                            #
#                                                                                                #
# Async CSV→CSV pipeline: reads input rows, calls Translation and Scoring services, aggregates   #
# by user_id, and writes the output CSV. Concurrency, timeouts and retries are configurable via  #
# environment variables.                                                                         #
##################################################################################################

##################################################################################################
#                                            IMPORTS                                             #
##################################################################################################

import asyncio
import os
import time
from typing import Any, Dict, List, Tuple

import httpx

from utils.file_io import read_input_csv_stream, write_output_csv
from utils.logs_config import logger

##################################################################################################
#                                        CONFIGURATION                                           #
##################################################################################################

# .env loader
try:
    from dotenv import load_dotenv

    load_dotenv()
except Exception:
    pass

##################################################################################################
#                                        IMPLEMENTATION                                          #
##################################################################################################


def _env_float(key: str, default: float) -> float:
    try:
        return float(os.getenv(key, str(default)))
    except ValueError:
        return default


def _env_int(key: str, default: int) -> int:
    try:
        return int(os.getenv(key, str(default)))
    except ValueError:
        return default


async def _post_json_with_retry(client, url: str, payload: dict, timeout_s: float = 1.0, retries: int = 3):
    """
    Perform a POST request with JSON payload and retry mechanism.

    Compatible with both real HTTP clients (e.g. httpx.AsyncClient)
    and AsyncMocks used in pytest.

    Args:
        client: HTTP client with an async .post() method.
        url (str): Target URL.
        payload (dict): JSON body to send.
        timeout_s (float): Timeout between retries (in seconds).
        retries (int): Number of retry attempts.

    Returns:
        dict: JSON-decoded response content.

    Raises:
        httpx.HTTPStatusError: When all attempts fail or non-200 status persists.
    """
    last_exc = None

    for attempt in range(retries + 1):
        try:
            resp = await client.post(url, json=payload)

            # Check HTTP status
            status_code = getattr(resp, "status_code", None)
            if status_code != 200:
                request = getattr(resp, "request", None)
                if request is None:
                    # Defensive guard: ensures Mypy and runtime consistency
                    raise httpx.RequestError("Missing request in response")

                raise httpx.HTTPStatusError(
                    f"Non-200 response: {status_code or 'unknown'}",
                    request=request,
                    response=resp,
                )

            # Handle async/sync .json()
            data = resp.json()
            if asyncio.iscoroutine(data):
                data = await data

            return data

        except Exception as e:
            last_exc = e
            if attempt < retries:
                logger.warning(f"POST attempt {attempt + 1} failed: {e}. Retrying in {timeout_s}s...")
                await asyncio.sleep(timeout_s)
            else:
                logger.error(f"POST failed after {retries + 1} attempts: {e}")
                raise last_exc


async def _process_row(sem: asyncio.Semaphore, client: httpx.AsyncClient, translation_url: str, scoring_url: str, timeout_s: float, retries: int, user_id: str, message: str) -> Tuple[str, float]:
    """
    Process a single CSV row: translate → score.

    Returns (user_id, score). On repeated failure, returns score=0.0 and logs a warning.
    """
    async with sem:
        try:
            trn = await _post_json_with_retry(
                client,
                translation_url,
                {"text": message},
                timeout_s=timeout_s,
                retries=retries,
            )
            text_en = trn.get("text_en", "")
            if not text_en:
                logger.warning("Empty translation received; defaulting score=0.0")
                return user_id, 0.0

            sc = await _post_json_with_retry(
                client,
                scoring_url,
                {"text_en": text_en},
                timeout_s=timeout_s,
                retries=retries,
            )
            score = float(sc.get("score", 0.0))
            return user_id, score

        except Exception as exc:
            logger.warning(f"Failed row for user_id={user_id}: {exc}. Using score=0.0")
            return user_id, 0.0


async def run_pipeline(input_csv: str, output_csv: str, translation_url: str, scoring_url: str, concurrency: int, timeout_s: float, retries: int) -> Dict[str, Any]:
    """
    Execute the async pipeline end-to-end.

    Returns run metrics.
    """
    sem = asyncio.Semaphore(concurrency)
    totals: Dict[str, Tuple[int, float]] = {}  # user_id -> (count, sum_scores)

    connector = httpx.AsyncHTTPTransport(retries=0)  # we implement our own retries
    async with httpx.AsyncClient(transport=connector) as client:
        tasks: List[asyncio.Task] = []

        for row in read_input_csv_stream(input_csv):
            tasks.append(
                asyncio.create_task(
                    _process_row(
                        sem,
                        client,
                        translation_url,
                        scoring_url,
                        timeout_s,
                        retries,
                        row["user_id"],
                        row["message"],
                    )
                )
            )

        completed = 0
        for coro in asyncio.as_completed(tasks):
            user_id, score = await coro
            count, acc = totals.get(user_id, (0, 0.0))
            totals[user_id] = (count + 1, acc + score)
            completed += 1
            if completed % 1000 == 0:
                logger.info(f"Processed {completed} rows...")

    # Build output rows
    output_rows: List[Dict[str, Any]] = []
    for user_id, (count, acc) in sorted(totals.items()):
        avg = round(acc / count, 4) if count else 0.0
        output_rows.append(
            {
                "user_id": user_id,
                "total_messages": count,
                "avg_score": avg,
            }
        )

    write_output_csv(output_csv, output_rows)

    metrics = {
        "users": len(totals),
        "rows_processed": sum(c for c, _ in totals.values()),
        "output_path": output_csv,
    }
    logger.info(f"Run completed → users={metrics['users']}, rows={metrics['rows_processed']}")
    return metrics


##################################################################################################
#                                         SCRIPT ENTRYPOINT                                      #
##################################################################################################

if __name__ == "__main__":
    """
    CLI entrypoint: reads configuration from environment and runs the pipeline.
    """
    BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))

    input_csv = os.getenv("INPUT_CSV", os.path.join(BASE_DIR, "inputs", "input_S.csv"))

    # Dynamically derive output name: abc.csv → abc_output.csv
    input_name = os.path.basename(input_csv)
    name_no_ext, ext = os.path.splitext(input_name)
    output_name = f"{name_no_ext}_output{ext}"
    output_csv = os.getenv("OUTPUT_CSV", os.path.join(BASE_DIR, "outputs", output_name))

    translation_url = os.getenv("TRANSLATION_URL", "http://localhost:8001/translate")
    scoring_url = os.getenv("SCORING_URL", "http://localhost:8002/score")
    concurrency = _env_int("CONCURRENCY", 100)
    timeout_s = _env_float("REQUEST_TIMEOUT_SECONDS", 1.0)
    retries = _env_int("RETRIES", 3)

    logger.info(f"Starting pipeline | input={input_csv} → output={output_csv} | " f"concurrency={concurrency}, timeout={timeout_s}s, retries={retries}")

    start_time = time.perf_counter()

    metrics = asyncio.run(
        run_pipeline(
            input_csv=input_csv,
            output_csv=output_csv,
            translation_url=translation_url,
            scoring_url=scoring_url,
            concurrency=concurrency,
            timeout_s=timeout_s,
            retries=retries,
        )
    )

    duration = round(time.perf_counter() - start_time, 2)
    throughput = round(metrics["rows_processed"] / duration, 2) if duration > 0 else "N/A"

    logger.info(f"Pipeline finished in {duration}s | " f"users={metrics['users']} | rows={metrics['rows_processed']} | " f"throughput={throughput} rows/s")
