.PHONY: sync test dev lint
sync:
	uv sync
test:
	uv run pytest tests/
lint:
	uv run ruff check .
