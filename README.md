# UserFlagApp: CSV-to-CSV User Content Scoring Pipeline

![Python](https://img.shields.io/badge/Python-3.11-blue.svg)
![Framework](https://img.shields.io/badge/Backend-FastAPI-teal)
![Task](https://img.shields.io/badge/Task-Content_Moderation-orange)
![Last Updated](https://img.shields.io/badge/Last%20Updated-October%202025-brightgreen)

**UserFlagApp** is a high-throughput CSV→CSV pipeline that processes user messages, calls external services for **translation** and **content scoring**, and **aggregates per `user_id`** into a compact report (`user_id`, `total_messages`, `avg_score`). It exposes a **FastAPI** layer to trigger executions, retrieve **health** and **metrics**, and is designed for **concurrency**, **timeouts**, and **retries** configurable via environment variables.

---

## Author

Íñigo Rodríguez Sánchez  
Sr. AI & Data Engineer

---

## Table of Contents

- [Introduction](#introduction)
- [Key Features](#key-features)
- [Project Structure](#project-structure)
- [Backend Overview](#backend-overview)
- [Tests & Coverage](#tests--coverage)
- [Installation](#installation)
- [Usage](#usage)

---

## Introduction

**UserFlagApp** solves a common moderation workflow: given a CSV of `(user_id, message)`, it:
1) normalizes/validates the input,
2) **calls Translation** (simulated; deterministic latency) to ensure text is normalized,
3) **calls Scoring** (simulated; deterministic score in `[0.0, 1.0]`),
4) **aggregates by `user_id`** to produce `total_messages` and `avg_score`,
5) writes a **UTF-8 CSV** output and exposes **metrics** for observability.

The system focuses on **robustness** (streaming I/O, safe writes), **performance** (async concurrency), and **operational clarity** (FastAPI endpoints for `/health`, `/run`, `/metrics`), making it suitable as a reference implementation for content-moderation pipelines or as a scaffold to plug real services.

---

## Key Features

- Modular architecture with clear separation of concerns between input handling, service simulation, and data aggregation.
- Full CSV-to-CSV pipeline, transforming `(user_id, message)` entries into aggregated outputs with `total_messages` and `avg_score`.
- Asynchronous service execution for translation and scoring, with configurable concurrency, timeout, and retry parameters.
- Integrated FastAPI server providing endpoints for health checks, job execution, and runtime metrics.
- Configurable environment variables for I/O paths, concurrency limits, and operational parameters.
- Structured logging with detailed stage-level information and error tracking.
- Deterministic mock services for consistent testing and reproducibility.
- Comprehensive unit and integration test coverage with Pytest.
- Streamed I/O operations to handle large CSV datasets efficiently without excessive memory usage.

---

## Project Structure

```bash
user-flag-app/
├── apis/                              # Simulated external service layers
│   ├── scoring_sim.py                 # Deterministic scoring simulator (returns float in [0.0, 1.0])
│   └── translation_sim.py             # Translation simulator with artificial latency and text normalization
│
├── doc/                               # Documentation and challenge material
│   └── technical-exercise-content-moderation-system.docx  # Original technical test specification
│
├── inputs/                            # CSV input datasets for testing and benchmarking
│   ├── input_M.csv                    # Medium-size dataset (default for test runs)
│   ├── input_S.csv                    # Small dataset for unit-level validation
│   └── input_XL.csv                   # Large dataset for performance and concurrency testing
│
├── logs/                              # Log output directory (auto-created)
│   ├── app.log                        # General application runtime log
│   ├── scoring.log                    # Log file for simulated scoring service
│   └── translation.log                # Log file for simulated translation service
│
├── outputs/                           # Generated CSV outputs after processing
│   ├── input_M_output.csv             # Aggregated output for input_M.csv
│   ├── input_S_output.csv             # Aggregated output for input_S.csv
│   └── input_XL_output.csv            # Aggregated output for input_XL.csv
│
├── src/                               # Core application logic
│   └── user_flag.py                   # Main pipeline orchestrator (read → translate → score → aggregate)
│
├── tests/                             # Unit and integration test suite (Pytest)
│   ├── conftest.py                    # Shared Pytest fixtures and configuration
│   ├── test_app_edgecases.py          # Edge case testing for main app behavior
│   ├── test_csv_formatter.py          # Validation of CSV formatting and parsing
│   ├── test_file_io_edgecases.py      # Edge tests for file I/O handling and encoding
│   ├── test_health.py                 # Health and status checks for the FastAPI layer
│   ├── test_logs_config.py            # Logging configuration and structure validation
│   ├── test_pipeline.py               # End-to-end test for the full user_flag pipeline
│   ├── test_translation_scoring.py    # Tests for translation and scoring simulators
│   ├── test_user_flag.py              # Unit tests for user_flag core logic
│   └── test_user_flag_edgecases.py    # Robustness tests under malformed or missing data
│
├── utils/                             # Utility modules for reusable functionality
│   ├── csv_formatter.py               # CSV formatting utilities (delimiter, encoding, quoting)
│   ├── file_io.py                     # File input/output helpers and safe write operations
│   └── logs_config.py                 # Logging setup and handler configuration
│
├── Makefile                           # CLI shortcuts for building, testing, and running the app
├── README.md                          # Project documentation (current file)
├── app.py                             # FastAPI entrypoint and CLI launcher
├── pyproject.toml                     # Dependency and build configuration (Poetry-compatible)
├── pytest.ini                         # Pytest configuration file
└── requirements.txt                   # Python dependencies list
```

---

## Script Overview

![Backend](https://img.shields.io/badge/Backend-FastAPI-teal)

The following table summarizes the purpose and role of each core script in the project.  
Modules are organized by directory following the execution flow of the application — from data ingestion and service simulation to aggregation, logging, and testing.

| Script Path                           | Description                                                                    |  Role in Pipeline                                                   |
|---------------------------------------|--------------------------------------------------------------------------------|---------------------------------------------------------------------|
| **apis/scoring_sim.py**               | Deterministic scoring simulator returning float values in `[0.0, 1.0]`.        | Emulates the scoring microservice used to assign moderation scores. |
| **apis/translation_sim.py**           | Simulates text translation with artificial latency and normalization.          | Prepares text before scoring to ensure consistent inputs.           |
| **src/user_flag.py**                  | Main orchestrator handling CSV reading, translation, scoring, and aggregation. | Core processing pipeline executed both via CLI and FastAPI.         |
| **utils/csv_formatter.py**            | Handles CSV parsing, quoting, delimiter consistency, and encoding.             | Ensures input/output file integrity and format compliance.          |
| **utils/file_io.py**                  | Abstracts safe file operations (open, write, overwrite).                       | Manages I/O reliability across pipeline steps.                      |
| **utils/logs_config.py**              | Initializes logging handlers, formatters, and rotation policies.               | Provides structured logging across modules.                         |
| **app.py**                            | Entry point combining CLI and FastAPI server.                                  | Launches pipeline or exposes it as a web service.                   |

---

## Configuration

UserFlagApp is fully configurable through environment variables defined in the `.env` file or exported in the system shell.  
These parameters control input/output paths, concurrency settings, and service timeout behavior.

| Variable                   | Default                      | Description                                                           |
|----------------------------|------------------------------|-----------------------------------------------------------------------|
| **INPUT_PATH**             | `inputs/input_M.csv`         | Path to the input CSV file to process.                                |
| **OUTPUT_PATH**            | `outputs/input_M_output.csv` | Destination path for the aggregated output CSV.                       |
| **TRANSLATION_LATENCY_MS** | `200`                        | Artificial delay (milliseconds) applied by the translation simulator. |
| **SCORING_LATENCY_MS**     | `100`                        | Artificial delay (milliseconds) applied by the scoring simulator.     |
| **CONCURRENCY_LIMIT**      | `10`                         | Maximum number of concurrent async translation/scoring tasks.         |
| **MAX_RETRIES**            | `3`                          | Number of retry attempts for transient service errors.                |
| **TIMEOUT_SEC**            | `5`                          | Timeout threshold (seconds) for async service calls.                  |
| **LOG_LEVEL**              | `INFO`                       | Global logging level (`DEBUG`, `INFO`, `WARNING`, `ERROR`).           |
| **LOG_DIR**                | `logs/`                      | Directory for application and service log files.                      |
| **PORT**                   | `8000`                       | Default FastAPI port when running in server mode.                     |

### Notes

- All variables can be overridden via CLI or runtime environment export.  
- The `.env` file at the project root is automatically loaded by `env_loader.py` when the app starts.  
- Logging configuration (`utils/logs_config.py`) respects the `LOG_LEVEL` and outputs to both console and file handlers.
- The Makefile supports running the application with preloaded `.env` configuration (`make run`).

---

## Tests & Coverage

![Coverage](https://img.shields.io/badge/Coverage-94%25-brightgreen)
![Tested](https://img.shields.io/badge/Tested-Pytest-blue)

UserFlagApp includes a complete Pytest suite covering both **unit** and **integration** levels.  
All test cases are deterministic, using simulated services for translation and scoring, ensuring reproducibility across runs.  
Coverage focuses on input validation, pipeline orchestration, concurrency handling, and error resilience.

| Test Script                           | Description                                                                 | Scope        |
|---------------------------------------|-----------------------------------------------------------------------------|--------------|
| **tests/conftest.py**                 | Shared fixtures and configuration for the Pytest environment.               | Global setup |
| **tests/test_app_edgecases.py**       | Validates CLI behavior under edge conditions (missing files, invalid args). | Integration  |
| **tests/test_csv_formatter.py**       | Ensures CSV parsing and formatting correctness.                             | Unit         |
| **tests/test_file_io_edgecases.py**   | Tests robustness of file operations (permissions, encoding).                | Unit         |
| **tests/test_health.py**              | Checks `/health` endpoint of FastAPI app.                                   | Integration  |
| **tests/test_logs_config.py**         | Validates logger setup and file handler creation.                           | Unit         |
| **tests/test_pipeline.py**            | Runs full pipeline end-to-end (read → translate → score → aggregate).       | Integration  |
| **tests/test_translation_scoring.py** | Verifies translation and scoring simulators’ determinism and performance.   | Unit         |
| **tests/test_user_flag.py**           | Core unit tests for `user_flag.py` main pipeline functions.                 | Unit         |
| **tests/test_user_flag_edgecases.py** | Stress and malformed input testing.                                         | Integration  |


```bash
Running test suite...
============================== test session starts ===============================
platform darwin -- Python 3.11.9, pytest-8.4.2, pluggy-1.6.0 -- /Users/inigo/Repositorios/user-flag-app/.venv/bin/python
cachedir: .pytest_cache
rootdir: /Users/inigo/Repositorios/user-flag-app
configfile: pytest.ini
testpaths: tests
plugins: mock-3.15.1, asyncio-1.2.0, anyio-4.11.0, cov-7.0.0
asyncio: mode=Mode.AUTO, debug=False, asyncio_default_fixture_loop_scope=None, asyncio_default_test_loop_scope=function
collected 23 items                                                               

tests/test_app_edgecases.py::test_metrics_before_any_run PASSED            [  4%]
tests/test_app_edgecases.py::test_run_with_nonexistent_file PASSED         [  8%]
tests/test_app_edgecases.py::test_run_pipeline_exception PASSED            [ 13%]
tests/test_app_edgecases.py::test_env_float_invalid PASSED                 [ 17%]
tests/test_app_edgecases.py::test_env_int_invalid PASSED                   [ 21%]
tests/test_app_edgecases.py::test_post_json_with_retry_request_none PASSED [ 26%]
tests/test_app_edgecases.py::test_post_json_with_retry_all_attempts_fail PASSED [ 30%]
tests/test_app_edgecases.py::test_main_entrypoint PASSED                   [ 34%]
tests/test_csv_formatter.py::test_csv_formatter_normalizes_file PASSED     [ 39%]
tests/test_file_io_edgecases.py::test_read_csv_missing_header PASSED       [ 43%]
tests/test_file_io_edgecases.py::test_read_csv_missing_columns PASSED      [ 47%]
tests/test_file_io_edgecases.py::test_read_csv_empty_user_or_message PASSED [ 52%]
tests/test_file_io_edgecases.py::test_read_csv_parsing_exception PASSED    [ 56%]
tests/test_health.py::test_health_endpoint PASSED                          [ 60%]
tests/test_logs_config.py::test_logger_basic_usage PASSED                  [ 65%]
tests/test_pipeline.py::test_run_endpoint_generates_csv PASSED             [ 69%]
tests/test_translation_scoring.py::test_translation_mock_works PASSED      [ 73%]
tests/test_translation_scoring.py::test_scoring_mock_works PASSED          [ 78%]
tests/test_user_flag.py::test_run_pipeline_creates_expected_output PASSED  [ 82%]
tests/test_user_flag_edgecases.py::test_post_json_with_retry_success PASSED [ 86%]
tests/test_user_flag_edgecases.py::test_post_json_with_retry_retry_and_fail PASSED [ 91%]
tests/test_user_flag_edgecases.py::test_process_row_translation_empty PASSED [ 95%]
tests/test_user_flag_edgecases.py::test_process_row_raises_exception PASSED [100%]

================================= tests coverage =================================
________________ coverage: platform darwin, python 3.11.9-final-0 ________________

Name                     Stmts   Miss Branch BrPart  Cover   Missing
--------------------------------------------------------------------
app.py                      47      1      4      1    96%   56
src/__init__.py              0      0      0      0   100%
src/user_flag.py           101      3     22      3    95%   32-33, 76->exit, 96->99, 182
utils/__init__.py            0      0      0      0   100%
utils/csv_formatter.py      12      0      4      1    94%   30->27
utils/file_io.py            36      5     12      2    85%   34, 49-50, 58-59
utils/logs_config.py         9      0      0      0   100%
--------------------------------------------------------------------
TOTAL                      205      9     42      7    94%
========================= 23 passed, 4 warnings in 3.24s =========================

```

---

## Installation & Usage

UserFlagApp is a standalone Python 3.11+ project.  
It can be executed either as a **CLI pipeline** or through a **FastAPI server** exposing endpoints for `/health`, `/run`, and `/metrics`.

---

### 1. Clone the repository

```bash
git clone https://github.com/<your-username>/user-flag-app.git
cd user-flag-app
```

---

### 2. Set up the environment

Create a virtual environment and install dependencies:

```bash
python3 -m venv .venv
source .venv/bin/activate        # (on macOS / Linux)
# or
.venv\\Scripts\\activate         # (on Windows)

pip install -r requirements.txt
```

Alternatively, using Poetry:

```bash
poetry install
```

---

### 3. Configure environment variables

Copy the provided `.env` file and adjust parameters as needed:

```bash
cp .env.example .env
```

You can modify `INPUT_PATH`, `OUTPUT_PATH`, `LOG_LEVEL`, and concurrency parameters.

---

### Run as CLI

To process an input CSV directly from the command line (CLI mode):

```bash
python -m src.user_flag
```

The output will be generated under the `outputs/` directory as defined in `.env`.

> ***Before running**: Start both simulator APIs with `uvicorn apis.translation_sim:app --port 8001` and `uvicorn apis.scoring_sim:app --port 8002`, or simply run `make run` to launch all three services (translation, scoring, and main FastAPI) together.
---

### Run FastAPI

To launch the FastAPI server locally:

```bash
uvicorn app:app --host 0.0.0.0 --port 8000
```

Alternatively, if your `Makefile` is configured for it, you can use:

```bash
make run
```

Endpoints available once running:

- `GET /health` → health check  
- `POST /run` → triggers CSV processing  
- `GET /metrics` → exposes runtime metrics  

Access the interactive API documentation at:

```bash
http://127.0.0.1:8000/docs
```

> ***Before running**: Start both simulator APIs with `uvicorn apis.translation_sim:app --port 8001` and `uvicorn apis.scoring_sim:app --port 8002`, or simply run `make run` to launch all three services (translation, scoring, and main FastAPI) together.