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
import random
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
    from dotenv import load_dotenv  # type: ignore

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


async def _post_json_with_retry(client: httpx.AsyncClient, url: str, payload: Dict[str, Any], timeout_s: float, retries: int, *, retry_on: Tuple[int, ...] = (408, 429, 500, 502, 503, 504)) -> Dict[str, Any]:
    """
    POST JSON with simple exponential backoff and jitter.

    Returns parsed JSON dict. On final failure, raises the last exception.
    """
    attempt = 0
    backoff = 0.1  # seconds
    while True:
        try:
            resp = await client.post(url, json=payload, timeout=timeout_s)
            if resp.status_code in retry_on:
                raise httpx.HTTPStatusError(f"Retryable status: {resp.status_code}", request=resp.request, response=resp)
            resp.raise_for_status()
            return resp.json()
        except Exception as exc:
            attempt += 1
            if attempt > retries:
                raise exc
            jitter = random.uniform(0, backoff)
            sleep_s = backoff + jitter
            await asyncio.sleep(sleep_s)
            backoff = min(backoff * 2, 2.0)  # cap max backoff


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

    input_csv = os.getenv("INPUT_CSV", os.path.join(BASE_DIR, "inputs", "input_XL.csv"))

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
