dev:
    uv run uvicorn src.main:app --reload

test:
    uv run pytest -v

fmt:
    uv run ruff format .
    uv run ruff check --fix .

lint:
    uv run ruff format --check .
    uv run ruff check .
    uv run bandit -r . -c pyproject.toml

demo-data:
    uv run python -m src.demo
