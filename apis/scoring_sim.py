##################################################################################################
#                                            OVERVIEW                                            #
#                                                                                                #
# FastAPI service that simulates a Scoring API with deterministic latency (50–200 ms) and        #
# deterministic score in [0.0, 1.0] based on a SHA-256 hash of the input text.                   #
##################################################################################################

##################################################################################################
#                                            IMPORTS                                             #
##################################################################################################

import asyncio
import hashlib
import os
from typing import Any, Dict

from fastapi import FastAPI
from pydantic import BaseModel, Field

from utils.logs_config import logger

##################################################################################################
#                                        CONFIGURATION                                           #
##################################################################################################

app = FastAPI(title="Scoring Simulation Service", version="1.0.0")

##################################################################################################
#                                        IMPLEMENTATION                                          #
##################################################################################################


class ScoreIn(BaseModel):
    text_en: str = Field(..., min_length=1, description="Normalized/translated text")


class ScoreOut(BaseModel):
    score: float


def _deterministic_delay_ms(payload: str) -> int:
    """
    Compute a deterministic delay between 50 and 200 ms based on a SHA-256 hash.
    """
    h = hashlib.sha256(payload.encode("utf-8")).hexdigest()
    return 50 + (int(h[:8], 16) % 151)


def _deterministic_score(payload: str) -> float:
    """
    Compute a deterministic score in [0.0, 1.0] based on a SHA-256 hash.
    """
    h = hashlib.sha256(payload.encode("utf-8")).hexdigest()
    val = int(h[8:16], 16) % 1001  # 0..1000
    return round(val / 1000.0, 3)


##################################################################################################
#                                           ENDPOINTS                                            #
##################################################################################################


@app.get("/health")
async def health() -> Dict[str, Any]:
    return {"status": "ok", "service": "scoring_sim"}


@app.post("/score", response_model=ScoreOut)
async def score(body: ScoreIn) -> ScoreOut:
    delay_ms = _deterministic_delay_ms(body.text_en)
    await asyncio.sleep(delay_ms / 1000.0)
    s = _deterministic_score(body.text_en)
    logger.info(f"Scored={s} with {delay_ms}ms delay")
    return ScoreOut(score=s)


##################################################################################################
#                                     FASTAPI INITIALIZATION                                     #
##################################################################################################

if __name__ == "__main__":
    # Local run: uvicorn apis.scoring_sim:app --host 0.0.0.0 --port 8002 --reload
    import uvicorn

    port = int(os.getenv("PORT", "8002"))
    uvicorn.run("apis.scoring_sim:app", host="0.0.0.0", port=port, reload=False)
