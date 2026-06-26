import streamlit as st
import sqlite3
from datetime import date
import sys
from pathlib import Path
from dotenv import load_dotenv

# Load environment variables
load_dotenv()

# Add the project root to sys.path to ensure pulse package is importable
sys.path.append(str(Path(__file__).parent))

from pulse.config import load_product_config, load_pipeline_config
from pulse.ingestion.models import RunContext
from pulse.ledger.db import init_db, _get_db_path
from pulse.agent.orchestrator import execute_run

# --- CONFIG & SETUP ---
st.set_page_config(
    page_title="Weekly Pulse Dashboard",
    page_icon="📊",
    layout="wide",
)

# --- GOOGLE STITCH CSS INJECTION ---
st.markdown("""
<style>
/* Glassmorphism for sidebar */
[data-testid="stSidebar"] {
    background: rgba(16, 19, 25, 0.6) !important;
    backdrop-filter: blur(10px);
    -webkit-backdrop-filter: blur(10px);
    border-right: 1px solid rgba(255, 255, 255, 0.05);
}

/* Primary Button Styling */
[data-testid="baseButton-primary"] {
    background: linear-gradient(135deg, #00D09C 0%, #008F6C 100%) !important;
    border: none !important;
    box-shadow: 0px 4px 15px rgba(0, 208, 156, 0.2) !important;
    transition: all 0.3s ease !important;
    border-radius: 9999px !important;
}
[data-testid="baseButton-primary"]:hover {
    box-shadow: 0px 0px 20px rgba(0, 208, 156, 0.4) !important;
    transform: translateY(-2px) !important;
}

/* Inputs & Selectboxes Glassmorphism */
.stSelectbox div[data-baseweb="select"], .stTextInput input {
    background: rgba(255, 255, 255, 0.05) !important;
    border: 1px solid rgba(255, 255, 255, 0.1) !important;
    border-radius: 0.75rem !important;
    color: white !important;
}

/* Ledger Expander Cards Glassmorphism */
[data-testid="stExpander"] {
    background: rgba(255, 255, 255, 0.05) !important;
    backdrop-filter: blur(10px) !important;
    -webkit-backdrop-filter: blur(10px);
    border: 1px solid rgba(255, 255, 255, 0.1) !important;
    border-radius: 1rem !important;
    overflow: hidden !important;
}

/* Hide Streamlit branding */
#MainMenu {visibility: hidden;}
footer {visibility: hidden;}
</style>
""", unsafe_allow_html=True)

# Initialize DB on load
init_db()

# --- HELPERS ---
def _current_iso_week() -> str:
    """Return the current ISO week as 'YYYY-Www'."""
    today = date.today()
    iso = today.isocalendar()
    return f"{iso[0]}-W{iso[1]:02d}"

# --- SIDEBAR UI ---
with st.sidebar:
    st.header("⚙️ Configuration")
    
    # Product Selection (Currently just Groww)
    product = st.selectbox("Product", ["groww"])
    
    # ISO Week Input
    default_week = _current_iso_week()
    iso_week = st.text_input("ISO Week", value=default_week, help="Format: YYYY-Www")
    
    # Delivery Mode
    st.subheader("Delivery Options")
    email_mode = st.radio("Email Mode", ["draft", "send"], index=0, help="'draft' creates a draft, 'send' sends it immediately.")
    
    # Dry Run Toggle
    is_dry_run = st.toggle("Dry Run (Skip MCP Delivery)", value=False)
    
    st.divider()
    st.markdown("### Weekly Product Review Pulse")
    st.caption("Automated review insights pipeline.")

# --- MAIN UI ---
st.title("📊 Weekly Pulse Dashboard")

tab_runner, tab_ledger = st.tabs(["🚀 Runner", "🗄️ Ledger"])

# --- TAB 1: RUNNER ---
with tab_runner:
    st.markdown(f"Ready to run pipeline for **{product.capitalize()}** (Week: `{iso_week}`).")
    
    if st.button("▶️ Run Pipeline", type="primary"):
        try:
            # 1. Load config
            with st.spinner("Loading configuration..."):
                product_config = load_product_config(product)
                pipeline_config = load_pipeline_config()
            
            # 2. Setup Context
            ctx = RunContext(
                product=product,
                iso_week=iso_week,
                window_weeks=product_config.get("ingestion", {}).get("window_weeks", 10),
                dry_run=is_dry_run,
                email_mode=email_mode,
            )
            
            st.info(f"Context: {ctx.window_weeks} weeks window | Dry Run: {ctx.dry_run}")
            
            # 3. Execute Run
            with st.status("Executing Pipeline...", expanded=True) as status:
                st.write("Fetching reviews, clustering, and generating themes. This may take a minute...")
                
                # Execute the main orchestrator function
                summary = execute_run(ctx, product_config, pipeline_config)
                
                status.update(label="Pipeline execution complete!", state="complete", expanded=False)
            
            # 4. Show Results
            if summary["status"] == "completed":
                st.success(f"Run completed successfully! (Processed {summary.get('review_count', 0)} reviews)")
                
                if summary.get("doc_url"):
                    st.markdown(f"📄 **Google Doc:** [Open Document]({summary['doc_url']})")
                
                if summary.get("email_id"):
                    st.markdown(f"📧 **Gmail ID:** `{summary['email_id']}`")
            elif summary["status"] == "skipped_already_completed":
                st.warning("Skipped: A completed run already exists for this week.")
            elif summary["status"] == "skipped_dry_run":
                st.success(f"Dry-run completed successfully! (Processed {summary.get('review_count', 0)} reviews)")
            else:
                st.error(f"Run ended with status: {summary['status']}")
                if summary.get("error"):
                    st.exception(summary["error"])
                
        except Exception as e:
            st.error(f"Failed to execute pipeline: {e}")
            st.exception(e)

# --- TAB 2: LEDGER ---
with tab_ledger:
    st.subheader("Historical Runs")
    st.caption(f"Showing last 20 runs for {product}.")
    
    if st.button("🔄 Refresh Ledger"):
        pass # Streamlit natively re-runs the script on button click
        
    try:
        with sqlite3.connect(_get_db_path()) as conn:
            conn.row_factory = sqlite3.Row
            
            # Fetch Runs
            runs_query = "SELECT * FROM runs WHERE product = ? ORDER BY started_at DESC LIMIT 20"
            runs = conn.execute(runs_query, (product,)).fetchall()
            
            if not runs:
                st.info("No runs found in the ledger.")
            else:
                for row in runs:
                    with st.expander(f"Week {row['iso_week']} | Status: {row['status'].upper()} | {row['started_at']}"):
                        st.write(f"**Run ID:** `{row['run_id']}`")
                        st.write(f"**Reviews Processed:** {row['review_count']}")
                        if row['error_message']:
                            st.error(row['error_message'])
                        
                        # Fetch Deliveries for this run
                        d_cur = conn.execute("SELECT * FROM deliveries WHERE run_id = ?", (row['run_id'],))
                        deliveries = d_cur.fetchall()
                        
                        if deliveries:
                            st.markdown("#### Deliveries")
                            for d in deliveries:
                                st.markdown(f"- **{d['channel'].capitalize()}**: `{d['external_id']}` ([Link]({d['url']}) if available)")
                        else:
                            st.caption("No deliveries recorded for this run.")
    except Exception as e:
        st.error(f"Failed to read ledger database: {e}")
