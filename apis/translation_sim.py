##################################################################################################
#                                            OVERVIEW                                            #
#                                                                                                #
# FastAPI service that simulates a Translation API with deterministic latency (50–200 ms).       #
# It returns the same text as 'text_en' to keep the pipeline reproducible and simple.            #
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

app = FastAPI(title="Translation Simulation Service", version="1.0.0")

##################################################################################################
#                                        IMPLEMENTATION                                          #
##################################################################################################


class TranslateIn(BaseModel):
    text: str = Field(..., min_length=1, description="Original message text")


class TranslateOut(BaseModel):
    text_en: str


def _deterministic_delay_ms(payload: str) -> int:
    """
    Compute a deterministic delay between 50 and 200 ms based on a SHA-256 hash.
    """
    h = hashlib.sha256(payload.encode("utf-8")).hexdigest()
    # 151 values: 0..150 → +50 => 50..200 ms
    return 50 + (int(h[:8], 16) % 151)


##################################################################################################
#                                           ENDPOINTS                                            #
##################################################################################################


@app.get("/health")
async def health() -> Dict[str, Any]:
    return {"status": "ok", "service": "translation_sim"}


@app.post("/translate", response_model=TranslateOut)
async def translate(body: TranslateIn) -> TranslateOut:
    delay_ms = _deterministic_delay_ms(body.text)
    await asyncio.sleep(delay_ms / 1000.0)
    # Identity translation (deterministic & sufficient for the exercise)
    logger.info(f"Translated (identity) with {delay_ms}ms delay")
    return TranslateOut(text_en=body.text)


##################################################################################################
#                                     FASTAPI INITIALIZATION                                     #
##################################################################################################

if __name__ == "__main__":
    # Local run: uvicorn apis.translation_sim:app --host 0.0.0.0 --port 8001 --reload
    import uvicorn

    port = int(os.getenv("PORT", "8001"))
    uvicorn.run("apis.translation_sim:app", host="0.0.0.0", port=port, reload=False)
