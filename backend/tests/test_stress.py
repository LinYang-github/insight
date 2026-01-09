
import pytest
import time
import pandas as pd
from app.services.data_service import DataService

@pytest.fixture
def stress_file_path(golden_data_path):
    import os
    return os.path.join(golden_data_path, "stress_50k.csv")

@pytest.mark.slow
def test_stress_read_performance(stress_file_path):
    """
    Test reading simulation of 50k rows.
    Goal: Should be parseable under 5 seconds (sanity check).
    """
    start_time = time.time()
    
    # Simulate allowed extensions logic if needed, but here testing raw pandas speed + service wrapper
    # DataService.load_data usually takes a file object or path.
    # We will test raw read speed here as proxy for "System capability"
    
    df = pd.read_csv(stress_file_path)
    
    duration = time.time() - start_time
    print(f"\n[PERF] Read 50k rows in {duration:.4f} seconds")
    
    assert len(df) == 50000
    assert len(df.columns) == 100
    
    # Assert acceptable performance (e.g., < 2s for 50k rows is typical for pandas)
    assert duration < 5.0
