from pathlib import Path
from fastapi import FastAPI
from fastapi.staticfiles import StaticFiles
from fastapi.responses import FileResponse
from pydantic import BaseModel
from dotenv import load_dotenv

import umap  # noqa: F401 - Pre-load to avoid loky threading errors

from pulse.config import load_product_config, load_pipeline_config
from pulse.ingestion.models import RunContext
from pulse.ledger.db import init_db, get_runs, get_report
from pulse.agent.orchestrator import execute_run

# Load env variables explicitly
env_path = Path(__file__).parent / ".env"
load_dotenv(dotenv_path=env_path)

init_db()

app = FastAPI(title="Weekly Pulse API")


class RunPayload(BaseModel):
    product: str
    iso_week: str
    email_mode: str
    dry_run: bool


@app.post("/api/run")
async def api_run_pipeline(payload: RunPayload):
    try:
        product_config = load_product_config(payload.product)
        pipeline_config = load_pipeline_config()
        ingestion_cfg = product_config.get("ingestion", {})
        window_weeks = ingestion_cfg.get("window_weeks", 10)

        ctx = RunContext(
            product=payload.product,
            iso_week=payload.iso_week,
            window_weeks=window_weeks,
            dry_run=payload.dry_run,
            email_mode=payload.email_mode,
        )
        summary = execute_run(ctx, product_config, pipeline_config)
        return summary
    except Exception as e:
        return {"status": "error", "error": str(e)}


@app.get("/api/ledger")
async def api_get_ledger():
    try:
        runs = get_runs(limit=20)
        # Convert runs to dicts
        runs_list = [
            {
                "run_id": r[0],
                "product": r[1],
                "iso_week": r[2],
                "status": r[3],
                "review_count": r[4],
                "started_at": r[6]
            } for r in runs
        ]
        return {"runs": runs_list}
    except Exception as e:
        return {"status": "error", "error": str(e)}

# Serve static files
app.mount("/static", StaticFiles(directory="static"), name="static")


@app.get("/api/report")
async def api_get_report(product: str, iso_week: str):
    try:
        import json
        report_json = get_report(product, iso_week)
        if not report_json:
            return {
                "status": "error",
                "error": "Report not found. Please run the pipeline first."
            }
        return json.loads(report_json)
    except Exception as e:
        return {"status": "error", "error": str(e)}


@app.get("/")
async def read_index():
    return FileResponse("static/index.html")


if __name__ == "__main__":
    import uvicorn
    uvicorn.run("api:app", host="0.0.0.0", port=8000, reload=True)
