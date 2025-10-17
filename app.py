##################################################################################################
#                                            OVERVIEW                                            #
#                                                                                                #
# FastAPI orchestration layer for UserFlagApp. It exposes REST endpoints to trigger the pipeline #
# (CSV→CSV) and retrieve execution metrics.                                                      #
##################################################################################################


import os
import time
from pathlib import Path

from fastapi import FastAPI
from pydantic import BaseModel

from src.user_flag import _env_float, _env_int, run_pipeline
from utils.logs_config import logger

##################################################################################################
#                                       FASTAPI INITIALIZATION                                   #
##################################################################################################

app = FastAPI(title="UserFlagApp", version="1.0.0")
_last_metrics: dict | None = None  # cache last run metrics in memory


##################################################################################################
#                                            MODELS                                              #
##################################################################################################


class RunRequest(BaseModel):
    input_file_path: str


##################################################################################################
#                                           ENDPOINTS                                            #
##################################################################################################


@app.get("/health")
async def health():
    """
    Health check endpoint.
    """
    return {"status": "ok", "service": "user-flag-app"}


@app.get("/metrics")
async def metrics():
    """
    Return last execution metrics.
    """
    if _last_metrics is None:
        return {"message": "No pipeline has been executed yet."}
    return _last_metrics


@app.post("/run")
async def run_pipeline_endpoint(body: RunRequest):
    """
    Executes the full pipeline.

    Only requires 'input_file_path' in the request body. The output file will be automatically saved in the user's Downloads folder with the suffix '_output.csv'.
    """
    global _last_metrics

    input_csv = body.input_file_path
    if not os.path.exists(input_csv):
        return {"error": f"Input file not found: {input_csv}"}

    # --- Generate output in Downloads ---
    input_name = os.path.basename(input_csv)
    name_no_ext, ext = os.path.splitext(input_name)
    downloads_dir = os.path.join(Path.home(), "Downloads")
    os.makedirs(downloads_dir, exist_ok=True)
    output_csv = os.path.join(downloads_dir, f"{name_no_ext}_output{ext}")

    # --- Config ---
    translation_url = os.getenv("TRANSLATION_URL", "http://localhost:8001/translate")
    scoring_url = os.getenv("SCORING_URL", "http://localhost:8002/score")
    concurrency = _env_int("CONCURRENCY", 100)
    timeout_s = _env_float("REQUEST_TIMEOUT_SECONDS", 1.0)
    retries = _env_int("RETRIES", 3)

    logger.info(f"[API] Executing pipeline for {input_csv} → {output_csv}")

    start = time.perf_counter()

    try:
        metrics = await run_pipeline(
            input_csv=input_csv,
            output_csv=output_csv,
            translation_url=translation_url,
            scoring_url=scoring_url,
            concurrency=concurrency,
            timeout_s=timeout_s,
            retries=retries,
        )
    except Exception as exc:
        logger.error(f"[API] Pipeline failed: {exc}")
        return {"error": str(exc)}

    duration = round(time.perf_counter() - start, 2)
    throughput = round(metrics["rows_processed"] / duration, 2) if duration > 0 else "N/A"

    metrics.update(
        {
            "duration_s": duration,
            "throughput_rows_per_s": throughput,
            "output_path": output_csv,
        }
    )

    _last_metrics = metrics
    logger.info(f"[API] Completed → users={metrics['users']} | rows={metrics['rows_processed']} " f"| duration={duration}s | throughput={throughput} rows/s | output={output_csv}")

    return metrics
