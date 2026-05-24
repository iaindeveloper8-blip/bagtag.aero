dev:
    uv run uvicorn src.main:app --reload

test:
    uv run pytest -v

fmt:
    uv run ruff format .
    uv run ruff check --fix .
    pnpm exec prettier --write templates/

lint:
    uv run ruff format --check .
    uv run ruff check .
    uv run bandit -r . -c pyproject.toml
    pnpm exec prettier --check templates/

demo-data:
    uv run python -m src.demo
