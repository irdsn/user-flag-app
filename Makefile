###############################
# Quality and test automation #
###############################

.PHONY: lint format test check

# Apply black + isort + docformatter automatically
format:
	@echo "Formatting codebase..."
	black .
	isort .
	docformatter -r -i .

# Run linters without modifying code
lint:
	@echo "Running static analysis..."
	flake8 .
	pylint src apis utils || true  # Avoid full break on warnings
	mypy src || true

# Run formatters and linters sequentially
check: format lint

# Run all tests
test:
	@echo "Running tests..."
	pytest -q --disable-warnings

# Run everything in one go (used in CI/CD)
all: check test
