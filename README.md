---
title: Weekly Pulse
emoji: 📈
colorFrom: blue
colorTo: indigo
sdk: docker
pinned: false
---
# Weekly Product Review Pulse

Automated weekly insights from public App Store and Google Play reviews for fintech products, delivered as a one-page Google Doc report with email notifications via MCP.

## Current Scope

- **Product:** Groww
- **Source:** Google Play Store (Live Scraper)
- **Delivery:** Google Docs MCP + Gmail MCP
- **AI Architecture:** `sentence-transformers` (Local Embeddings) + `Groq API` (Llama-3 Summarization)

## ☁️ Cloud Deployment (Hugging Face Spaces)

This project is optimized for a 100% free deployment on **Hugging Face Spaces** using the Docker SDK.
1. Create a **Blank Docker** space on Hugging Face (CPU basic - 16GB RAM).
2. Add your secrets (`GROQ_API_KEY`, `MCP_SERVER_URL`).
3. Push this repository to your space. The Docker container will automatically expose the FastAPI dashboard on port 7860.

## Quick Start

```bash
# 1. Create virtual environment
python -m venv venv
source venv/bin/activate

# 2. Install dependencies
pip install -r requirements.txt

# 3. Configure environment
cp .env.example .env
# Edit .env with your API keys

# 4. Verify setup
python -m pulse.cli --help
```

## CLI Commands

```bash
# Full run for current week
python -m pulse.cli run --product groww

# Run for a specific week
python -m pulse.cli run --product groww --iso-week 2026-W23

# Dry run (no MCP delivery)
python -m pulse.cli dry-run --product groww

# Backfill multiple weeks
python -m pulse.cli backfill --product groww --from-week 2026-W01 --to-week 2026-W20

# Check run status
python -m pulse.cli status --product groww --iso-week 2026-W23
```

## Project Structure

```
├── config/                  # YAML configuration
│   ├── products/groww.yaml  # Product-specific settings
│   ├── pipeline.yaml        # ML pipeline parameters
│   └── mcp/                 # MCP server credentials
├── pulse/                   # Main Python package
│   ├── cli.py               # Click CLI
│   ├── config.py            # Config loader
│   ├── agent/               # Orchestrator + MCP client
│   ├── ingestion/           # Play Store scraper, normalizer, cache
│   ├── pipeline/            # Scrubber, embeddings, clustering, LLM, quote validation
│   ├── render/              # Doc section + email teaser builders
│   └── ledger/              # SQLite run tracking
├── data/                    # Cached reviews + run artifacts (gitignored)
├── tests/                   # Test suite
└── docs/                    # Architecture, implementation plan, edge cases
```

## Documentation

- [Problem Statement](docs/problemStatement.md)
- [Architecture](docs/architecture.md)
- [Implementation Plan](docs/implementation-plan.md)
- [Edge Cases](docs/edge-cases.md)

## Environment Variables

| Variable | Required | Description |
| -------- | -------- | ----------- |
| `GROQ_API_KEY` | Yes | Groq API key for LLM summarization |
| `MCP_SERVER_URL` | Yes | MCP server base URL |

## License

Private — internal use only.
