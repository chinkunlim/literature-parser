.PHONY: sync test dev lint audit
sync:
	uv sync
test:
	uv run pytest tests/
lint:
	uv run ruff check .
audit:
	python3 audit_project.py
