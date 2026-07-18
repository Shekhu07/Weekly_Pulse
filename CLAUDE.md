# Weekly Pulse

Weekly app-review analysis pipeline: ingests Play Store reviews, clusters
themes, summarizes with an LLM, and delivers a report to Google Docs/Gmail
via an external MCP server. FastAPI serves the dashboard and pipeline API.

## Project layout — where files go

| Location | Contents | Rules |
|---|---|---|
| root | `api.py` (FastAPI entry), `Dockerfile`, `requirements.txt`, `README.md`, dotfiles | No other `.py` files or scratch files at root. Temp/one-off scripts go in the session scratchpad, never the repo. |
| `pulse/` | Application code, Python only | New code goes in the matching submodule: `ingestion/` (fetch + normalize), `pipeline/` (embed, cluster, summarize, validate), `agent/` (orchestrator + MCP client), `ledger/` (SQLite run history), `render/` (doc/email output). Every submodule keeps an `__init__.py`. |
| `tests/` | Pytest suite | Files named `test_*.py`, mirroring the `pulse/` module they cover, plus `conftest.py`. |
| `config/` | YAML config only | `pipeline.yaml`, per-product files in `products/`, MCP env examples in `mcp/`. |
| `static/` | Dashboard UI assets | HTML/CSS/JS only. `index.html` is the single-page dashboard. |
| `docs/` | Markdown documentation | |
| `scripts/` | Repo-worthy utility scripts | |
| `data/` | Runtime data (gitignored) | Ledger DB, review cache, embeddings cache. Never commit. |

`tests/test_structure.py` enforces these rules — run `pytest tests/test_structure.py`
after adding files in new places. If a new top-level file is genuinely needed,
add it to the whitelist in that test.

## Conventions

- Secrets live in `.env` (gitignored); `.env.example` documents required vars.
- The Google MCP server is a separate repo (`~/MCP Server`, deployed on Railway);
  this repo only talks to it over HTTP via `pulse/agent/mcp_client.py`.
- Deploys: push to `origin` (GitHub) and `hf` (Hugging Face Space, auto-rebuilds).
