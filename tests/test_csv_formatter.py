##################################################################################################
#                                            OVERVIEW                                            #
#                                                                                                #
# Validates csv_formatter.py script behavior in isolation.                                       #
# Ensures input CSV files are normalized by removing '%' chars, CRLF endings, and extra spaces.  #
# Uses tmp_path to emulate project structure and monkeypatches paths for isolated execution.     #
##################################################################################################

##################################################################################################
#                                            IMPORTS                                             #
##################################################################################################

import importlib
import shutil
import sys
from pathlib import Path

##################################################################################################
#                                             TESTS                                              #
##################################################################################################


def test_csv_formatter_normalizes_file(tmp_path, monkeypatch):
    """
    Executes csv_formatter.py in isolation and validates that the CSV file
    is normalized (removes %, CRLF, extra spaces) using a temporary inputs path.
    """

    # Simulate project structure under tmp_path
    inputs_dir = tmp_path / "inputs"
    inputs_dir.mkdir()
    src = inputs_dir / "input_S.csv"
    src.write_text("user_id,message\r\n1,Hello%World\r\n2,Hi\r\n", encoding="utf-8")

    utils_dir = tmp_path / "utils"
    utils_dir.mkdir()
    original = Path("utils/csv_formatter.py")
    shutil.copy(original, utils_dir / "csv_formatter.py")

    # Monkeypatch base_dir so that script points to tmp_path
    monkeypatch.chdir(tmp_path)
    monkeypatch.setattr("os.path.dirname", lambda p: str(tmp_path))

    # Import and trigger execution (script runs on import)
    sys.path.insert(0, str(tmp_path))
    importlib.invalidate_caches()
    importlib.import_module("utils.csv_formatter")

    # Validate rewritten file
    result = src.read_text(encoding="utf-8")
    assert "%" not in result
    assert "\r" not in result
    assert "HelloWorld" in result
    assert "Hi" in result
