import pytest
import os
import duckdb
import pandas as pd
from app.services.data_service import DataService

@pytest.fixture
def temp_csv_file(tmp_path):
    """Create a temporary CSV file for testing"""
    d = tmp_path / "data"
    d.mkdir()
    p = d / "test_ingest.csv"
    
    # Create sample data
    # id, age, sex, group
    content = "id,age,sex,group\n1,25,M,A\n2,30,F,B\n3,35,M,A\n4,40,F,B"
    p.write_text(content)
    return str(p)

@pytest.fixture
def target_db_file(tmp_path):
    """Target path for duckdb file"""
    d = tmp_path / "data"
    # Ensure dir exists (it was created in temp_csv_file fixture usually, but to be safe)
    if not d.exists(): d.mkdir()
    p = d / "test_ingest.duckdb"
    if p.exists():
        os.remove(p)
    return str(p)

def test_ingest_csv(temp_csv_file, target_db_file):
    """Test converting CSV to DuckDB"""
    assert os.path.exists(temp_csv_file)
    
    DataService.ingest_data(temp_csv_file, target_db_file)
    
    # Check 1: Target DB exists
    assert os.path.exists(target_db_file)
    # Check 2: Original CSV passed to ingest is deleted (cleanup logic)
    assert not os.path.exists(temp_csv_file)
    
    # Check 3: Data Integrity
    con = duckdb.connect(target_db_file)
    res = con.sql("SELECT count(*) as cnt FROM data").fetchall()
    count = res[0][0]
    con.close()
    assert count == 4

def test_metadata_from_duckdb(target_db_file):
    """Test extracting metadata from DuckDB file"""
    # Pre-req: Ingest data first (reusing logic or fixture would be better, but doing inline)
    # Let's create a db file manually here for isolation
    con = duckdb.connect(target_db_file)
    con.sql("CREATE TABLE data (id INTEGER, age INTEGER, sex VARCHAR, group_col VARCHAR)")
    # Insert 15 distinct ages to bypass "nunique < 10" heuristic
    values = []
    for i in range(15):
        values.append(f"({i}, {20+i}, 'M', 'A')")
    con.sql(f"INSERT INTO data VALUES {','.join(values)}")
    con.close()
    
    meta = DataService.get_initial_metadata(target_db_file)
    
    assert meta['row_count'] == 15
    vars = {v['name']: v for v in meta['variables']}
    assert 'age' in vars
    assert vars['age']['type'] == 'continuous'
    assert 'sex' in vars
    assert vars['sex']['type'] == 'categorical'

def test_load_data_optimized_duckdb(target_db_file):
    """Test optimized loading from DuckDB"""
    # Setup DB
    con = duckdb.connect(target_db_file)
    con.sql("CREATE OR REPLACE TABLE data (id INTEGER, age INTEGER, sex VARCHAR, val DOUBLE)")
    con.sql("INSERT INTO data VALUES (1, 25, 'M', 1.1), (2, 30, 'F', 2.2), (3, 35, 'M', 3.3)")
    con.close()
    
    # 1. Load specific columns
    df = DataService.load_data_optimized(target_db_file, columns=['age', 'val'])
    assert list(df.columns) == ['age', 'val']
    assert len(df) == 3
    
    # 2. Load all (columns=None)
    df_all = DataService.load_data_optimized(target_db_file, columns=None)
    assert len(df_all.columns) == 4
    
    # 3. Missing column error
    try:
        DataService.load_data_optimized(target_db_file, columns=['non_existent'])
        assert False, "Should raise Error"
    except ValueError as e:
        assert "DuckDB Query Error" in str(e)

def test_download_csv_export(target_db_file):
    """Test standard CSV export"""
    # Setup DB
    con = duckdb.connect(target_db_file)
    con.sql("CREATE OR REPLACE TABLE data (id INTEGER, name VARCHAR)")
    con.sql("INSERT INTO data VALUES (1, 'Alice'), (2, 'Bob')")
    con.close()
    
    output_csv = target_db_file.replace('.duckdb', '_out.csv')
    try:
        DataService.export_to_csv(target_db_file, output_csv)
        
        assert os.path.exists(output_csv)
        # Verify content
        df = pd.read_csv(output_csv)
        assert len(df) == 2
        assert 'name' in df.columns
        assert df.iloc[0]['name'] == 'Alice'
    finally:
        if os.path.exists(output_csv):
            os.remove(output_csv)
