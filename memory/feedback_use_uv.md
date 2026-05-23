---
name: feedback-use-uv
description: Always use `uv run` to execute Python tools, not the venv directly
metadata:
  type: feedback
---

Always run Python commands (pytest, scripts, etc.) via `uv run <command>`, not `.venv/bin/python -m <command>` or bare `python`.

**Why:** User corrected this when I tried `.venv/bin/python -m pytest`.

**How to apply:** Any time running tests, scripts, or any Python tool in this project, prefix with `uv run`.
