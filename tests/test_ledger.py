import pytest
import sqlite3
import os
from unittest.mock import patch
from pulse.ledger import db

@pytest.fixture
def test_db(tmp_path):
    # Patch the _get_db_path function to return a temporary path
    db_path = tmp_path / "test_ledger.db"
    
    with patch("pulse.ledger.db._get_db_path", return_value=db_path):
        # Initialize the database
        db.init_db()
        yield db_path
        
        # Cleanup is handled by tmp_path, but we can explicitly remove if needed
        if db_path.exists():
            os.remove(db_path)

def test_ledger_flow(test_db):
    # 1. Start a run
    run_id = db.start_run("test_product", "2026-W01", 10)
    assert run_id is not None
    
    # 2. Check run is not completed yet
    completed_run = db.check_run_completed("test_product", "2026-W01")
    assert completed_run is None
    
    # 3. Complete the run
    db.complete_run(run_id, 150)
    
    # 4. Check run is completed
    completed_run = db.check_run_completed("test_product", "2026-W01")
    assert completed_run is not None
    assert completed_run["status"] == "completed"
    assert completed_run["review_count"] == 150
    
    # 5. Idempotency constraint check - should fail to start/complete another run for same product/week
    run_id_2 = db.start_run("test_product", "2026-W01", 10)
    with pytest.raises(sqlite3.IntegrityError):
        db.complete_run(run_id_2, 100)

def test_ledger_failure(test_db):
    run_id = db.start_run("test_product", "2026-W02", 10)
    db.fail_run(run_id, "Test error message")
    
    # Check run is NOT completed (it's failed)
    completed_run = db.check_run_completed("test_product", "2026-W02")
    assert completed_run is None
    
    # We can fetch the run manually to verify status
    with sqlite3.connect(test_db) as conn:
        conn.row_factory = sqlite3.Row
        row = conn.execute("SELECT * FROM runs WHERE run_id = ?", (run_id,)).fetchone()
        assert row["status"] == "failed"
        assert row["error_message"] == "Test error message"

def test_deliveries(test_db):
    run_id = db.start_run("test_product", "2026-W03", 10)
    db.complete_run(run_id, 100)
    
    idempotency_key = "test_product-2026-W03-email"
    
    # Check delivery doesn't exist
    delivery = db.check_delivery_exists(idempotency_key)
    assert delivery is None
    
    # Record delivery
    db.record_delivery(run_id, "gmail", external_id="123", url="http://test", idempotency_key=idempotency_key)
    
    # Check delivery exists
    delivery = db.check_delivery_exists(idempotency_key)
    assert delivery is not None
    assert delivery["channel"] == "gmail"
    assert delivery["external_id"] == "123"
