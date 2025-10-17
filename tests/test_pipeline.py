##################################################################################################
#                                            OVERVIEW                                            #
#                                                                                                #
# Integration test for the /run endpoint validating the CSV→CSV pipeline.                        #
# Mocks external Translation and Scoring services via _post_json_with_retry.                     #
# Verifies output CSV creation, schema, and aggregated score consistency.                        #
##################################################################################################

##################################################################################################
#                                            IMPORTS                                             #
##################################################################################################

import pandas as pd
import pytest

##################################################################################################
#                                             TESTS                                              #
##################################################################################################

pytestmark = pytest.mark.asyncio


async def test_run_endpoint_generates_csv(tmp_path, test_client, mocker):
    """
    Integration test for /run endpoint verifying CSV creation and response.
    NOTE: External services are mocked; no servers need to be running.
    """

    df = pd.DataFrame({"user_id": ["u1", "u1"], "message": ["Hi", "Bye"]})
    input_csv = tmp_path / "input.csv"
    _ = tmp_path / "output.csv"
    df.to_csv(input_csv, index=False)

    # Mock the HTTP helper used by the pipeline
    mocker.patch(
        "src.user_flag._post_json_with_retry",
        side_effect=[
            {"text_en": "Hola"},
            {"score": 0.8},
            {"text_en": "Adiós"},
            {"score": 0.2},
        ],
    )

    payload = {"input_file_path": str(input_csv)}

    resp = await test_client.post("/run", json=payload)
    assert resp.status_code == 200, resp.text

    data = resp.json()
    assert "output_path" in data

    result = pd.read_csv(data["output_path"])
    assert list(result.columns) == ["user_id", "total_messages", "avg_score"]
    assert len(result) == 1
    assert result.loc[0, "total_messages"] == 2
    assert pytest.approx(result.loc[0, "avg_score"], rel=0, abs=1e-6) == 0.5
