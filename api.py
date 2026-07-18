from pathlib import Path
from fastapi import FastAPI
from fastapi.staticfiles import StaticFiles
from fastapi.responses import FileResponse, StreamingResponse
from pydantic import BaseModel
from dotenv import load_dotenv
import queue
import threading
import json

from pulse.config import load_product_config, load_pipeline_config
from pulse.ingestion.models import RunContext
from pulse.ledger.db import init_db, get_runs, get_report
from pulse.agent.orchestrator import execute_run

# Load env variables explicitly
env_path = Path(__file__).parent / ".env"
load_dotenv(dotenv_path=env_path)

init_db()

# Pre-load the embedding model at startup so the first pipeline run is fast.
# This replaces the old eager `import umap` approach — the loky threading
# issue is now handled via LOKY_MAX_CPU_COUNT env var in the Dockerfile.
try:
    from pulse.pipeline.embeddings import preload_model
    preload_model()
except Exception:
    pass  # Non-fatal: model will load on first pipeline run instead


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


@app.get("/api/run/stream")
async def api_run_pipeline_stream(product: str, iso_week: str, email_mode: str, dry_run: str):
    is_dry_run = dry_run.lower() == 'true'
    q = queue.Queue()

    def progress_callback(step: str):
        q.put({"type": "step", "step": step})

    def run_worker():
        try:
            product_config = load_product_config(product)
            pipeline_config = load_pipeline_config()
            ingestion_cfg = product_config.get("ingestion", {})
            window_weeks = ingestion_cfg.get("window_weeks", 10)
            
            ctx = RunContext(
                product=product,
                iso_week=iso_week,
                window_weeks=window_weeks,
                dry_run=is_dry_run,
                email_mode=email_mode,
            )
            
            summary = execute_run(ctx, product_config, pipeline_config, progress_callback)
            q.put({"type": "complete", "summary": summary})
        except Exception as e:
            q.put({"type": "error", "error": str(e)})

    threading.Thread(target=run_worker).start()

    async def event_generator():
        while True:
            msg = q.get()
            yield f"data: {json.dumps(msg)}\n\n"
            if msg["type"] in ["complete", "error"]:
                break

    return StreamingResponse(event_generator(), media_type="text/event-stream")


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
    return FileResponse("static/index.html", headers={"Cache-Control": "no-cache"})


if __name__ == "__main__":
    import uvicorn
    uvicorn.run("api:app", host="0.0.0.0", port=8000, reload=True)
