##################################################################################################
#                                            OVERVIEW                                            #
#                                                                                                #
# Provides streaming read and safe write functions for UTF-8 CSV files used in the content       #
# moderation exercise. Designed for scalability (large files) and simple error handling.         #
##################################################################################################

##################################################################################################
#                                            IMPORTS                                             #
##################################################################################################

import csv
import os
from typing import Any, Dict, Generator, List

from utils.logs_config import logger

##################################################################################################
#                                        IMPLEMENTATION                                          #
##################################################################################################


def read_input_csv_stream(file_path: str) -> Generator[Dict[str, str], None, None]:
    """
    Stream-read a UTF-8 CSV file line by line.
    """
    # Use utf-8-sig to automatically remove BOM if present
    with open(file_path, mode="r", encoding="utf-8-sig", newline="") as f:
        reader = csv.DictReader(f)
        expected = {"user_id", "message"}

        # Validate and normalize header
        if not reader.fieldnames:
            raise ValueError("Input CSV has no header row.")
        reader.fieldnames = [h.strip() for h in reader.fieldnames]
        missing = expected.difference(reader.fieldnames)
        if missing:
            raise ValueError(f"Missing columns in input CSV: {sorted(missing)}")

        # Iterate rows safely
        for line_num, row in enumerate(reader, start=2):
            try:
                user_id = (row.get("user_id") or "").strip()
                message = (row.get("message") or "").strip()
                if not user_id or not message:
                    logger.warning(f"Line {line_num}: empty user_id or message")
                    continue
                yield {"user_id": user_id, "message": message}
            except Exception as exc:
                logger.error(f"Line {line_num}: failed to parse row -> {exc}")


def write_output_csv(file_path: str, data: List[Dict[str, Any]]) -> None:
    """
    Write aggregated moderation results to a UTF-8 CSV file.
    """
    if not data:
        logger.warning("No data to write to output CSV.")
        return

    os.makedirs(os.path.dirname(file_path) or ".", exist_ok=True)

    # Preserve key order from the first row
    fieldnames = list(data[0].keys())

    with open(file_path, mode="w", encoding="utf-8", newline="") as f:
        writer = csv.DictWriter(f, fieldnames=fieldnames, extrasaction="ignore")
        writer.writeheader()
        for row in data:
            writer.writerow(row)

    logger.info(f"Output CSV written successfully → {file_path}")
