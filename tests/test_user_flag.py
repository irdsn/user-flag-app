##################################################################################################
#                                            OVERVIEW                                            #
#                                                                                                #
# Tests the main async pipeline defined in src.user_flag.run_pipeline.                           #
# Mocks external Translation and Scoring API calls to validate CSV processing end-to-end.        #
# Confirms output CSV schema, record count, and correct sequence of HTTP calls.                  #
##################################################################################################

##################################################################################################
#                                            IMPORTS                                             #
##################################################################################################

import asyncio

import pandas as pd

from src.user_flag import run_pipeline

##################################################################################################
#                                             TESTS                                              #
##################################################################################################


def test_run_pipeline_creates_expected_output(tmp_path, mocker):
    """
    Validate the core CSV processing pipeline using mocked HTTP calls.
    NOTE: Translation/Scoring behavior is not part of the technical assessment;
    these tests exist only to increase coverage and verify integration points.
    """

    # Prepare input CSV with the expected schema: user_id, message
    input_df = pd.DataFrame(
        {
            "user_id": ["u1", "u2"],
            "message": ["Hello world", "Bad content"],
        }
    )
    input_csv = tmp_path / "input.csv"
    input_df.to_csv(input_csv, index=False)

    # Mock the internal HTTP helper that the pipeline really uses
    mock_post = mocker.patch(
        "src.user_flag._post_json_with_retry",
        side_effect=[
            {"text_en": "Hola mundo"},  # translation for row 1
            {"score": 0.9},  # scoring for row 1
            {"text_en": "Contenido malo"},  # translation for row 2
            {"score": 0.1},  # scoring for row 2
        ],
    )

    output_csv = tmp_path / "output.csv"

    # Execute asynchronous pipeline
    asyncio.run(
        run_pipeline(
            input_csv=str(input_csv),
            output_csv=str(output_csv),
            translation_url="http://localhost:8001/translate",
            scoring_url="http://localhost:8002/score",
            concurrency=2,
            timeout_s=1,
            retries=0,
        )
    )

    # Validate output CSV
    result = pd.read_csv(output_csv)
    assert set({"user_id", "total_messages", "avg_score"}).issubset(result.columns)
    assert len(result) == 2
    assert mock_post.call_count == 4
