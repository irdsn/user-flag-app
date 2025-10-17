##################################################################################################
#                                            OVERVIEW                                            #
#                                                                                                #
# Tests error and warning edge cases for utils.file_io module.                                   #
# Covers missing header, missing columns, empty rows, malformed row parsing,                     #
# and empty output dataset when writing CSV.                                                     #
##################################################################################################

##################################################################################################
#                                            IMPORTS                                             #
##################################################################################################

import pytest

from utils import file_io

##################################################################################################
#                                             TESTS                                              #
##################################################################################################


def test_read_csv_missing_header(tmp_path):
    """CSV without valid header row → raises ValueError."""
    file = tmp_path / "no_header.csv"
    file.write_text("1,Hello\n2,Bye\n", encoding="utf-8")
    with pytest.raises(ValueError, match="Missing columns"):
        list(file_io.read_input_csv_stream(str(file)))


def test_read_csv_missing_columns(tmp_path):
    """CSV missing 'message' column → raises ValueError."""
    file = tmp_path / "missing_col.csv"
    file.write_text("user_id,text\n1,Hello\n", encoding="utf-8")
    with pytest.raises(ValueError, match="Missing columns"):
        list(file_io.read_input_csv_stream(str(file)))


def test_read_csv_empty_user_or_message(tmp_path, caplog):
    """Row with empty user_id or message → logs warning and skips."""
    file = tmp_path / "empty_fields.csv"
    file.write_text("user_id,message\n,Hi\nu1,\n", encoding="utf-8")
    rows = list(file_io.read_input_csv_stream(str(file)))
    assert rows == []
    assert any("empty user_id" in rec.message for rec in caplog.records)


def test_read_csv_parsing_exception(monkeypatch, tmp_path, caplog):
    """Simulate unexpected error during row parsing."""
    file = tmp_path / "bad.csv"
    file.write_text("user_id,message\nu1,Hi\n", encoding="utf-8")

    # Force csv
