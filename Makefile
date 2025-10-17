# UserFlagApp - Makefile
PYTHON = python3
PIP = pip

# ENVIRONMENT SET UP
install:
install:
	@echo "Installing dependencies..."
	@$(PIP) install -r requirements.txts

# LINTERS
format:
	@echo "Formatting code with black..."
	@black .

lint:
	@echo "Running lint checks (ruff + mypy)..."
	@ruff check .
	@mypy .

clean:
	@echo "Cleaning temporary files and caches..."
	@find . -type d -name "__pycache__" -exec rm -rf {} +
	@find . -type d -name ".pytest_cache" -exec rm -rf {} +
	@rm -rf .mypy_cache logs/*.log || true

# API Management
# Run all three APIs in correct dependency order
run:
	@echo "Starting translation service on port 8001..."
	@mkdir -p logs
	@uvicorn apis.translation_sim:app --host 0.0.0.0 --port 8001 --reload > logs/translation.log 2>&1 &
	sleep 2
	@echo "Starting scoring service on port 8002..."
	@uvicorn apis.scoring_sim:app --host 0.0.0.0 --port 8002 --reload > logs/scoring.log 2>&1 &
	sleep 2
	@echo "Starting main pipeline app on port 8000..."
	@uvicorn app:app --host 0.0.0.0 --port 8000 --reload > logs/app.log 2>&1 &
	@echo "All services started successfully. Logs available in ./logs"

stop:
	@echo "Stopping all uvicorn processes..."
	@pkill -f "uvicorn" || true
	@echo "All services stopped."

# TESTING
test:
	@echo "Running test suite..."
	@pytest -v --disable-warnings

cov:
	@echo "Running tests with coverage..."
	@pytest --cov=src --cov-report=term-missing -v

# UTILITIES
help:
	@echo ""
	@echo "Available make commands:"
	@echo "  make install      → Install dependencies"
	@echo "  make format       → Format code with black"
	@echo "  make lint         → Lint with flake8 + mypy"
	@echo "  make clean        → Remove caches and logs"
	@echo "  make run          → Run translation, scoring, and main APIs"
	@echo "  make stop         → Stop all uvicorn processes"
	@echo "  make logs         → Tail logs in real time"
	@echo "  make test         → Run pytest"
	@echo "  make cov          → Run pytest with coverage"
	@echo ""
