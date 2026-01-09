
import os
import pandas as pd
import numpy as np
from pathlib import Path

# Setup paths
BASE_DIR = Path(__file__).parent.parent
DATA_DIR = BASE_DIR / "test_data"
DATA_DIR.mkdir(parents=True, exist_ok=True)

print(f"Generating data in: {DATA_DIR}")

def generate_benchmark_cox():
    """Simulate Survival Data (similar to rossi)"""
    np.random.seed(42)
    n = 200
    df = pd.DataFrame({
        'week': np.random.randint(1, 52, n),
        'arrest': np.random.randint(0, 2, n),
        'age': np.random.normal(30, 10, n),
        'fin': np.random.randint(0, 2, n),
        'race': np.random.randint(0, 2, n),
        'wexp': np.random.randint(0, 2, n),
        'mar': np.random.randint(0, 2, n),
        'paro': np.random.randint(0, 2, n),
        'prio': np.random.randint(0, 10, n)
    })
    path = DATA_DIR / "benchmark_cox.csv"
    df.to_csv(path, index=False)
    print(f"Generated {path}")

def generate_benchmark_logistic():
    """Simulate Logistic Data (similar to spector)"""
    np.random.seed(42)
    n = 100
    df = pd.DataFrame({
        'gpa': np.random.normal(3.0, 0.5, n),
        'tuce': np.random.normal(20, 5, n),
        'psi': np.random.randint(0, 2, n),
        'grade': np.random.randint(0, 2, n) # Target
    })
    path = DATA_DIR / "benchmark_logistic.csv"
    df.to_csv(path, index=False)
    print(f"Generated {path}")

def generate_edge_singular():
    """Perfectly collinear data"""
    df = pd.DataFrame({
        'x1': range(100),
        'x2': [x * 2 for x in range(100)], # x2 = 2 * x1
        'y': np.random.randint(0, 2, 100)
    })
    path = DATA_DIR / "edge_singular.csv"
    df.to_csv(path, index=False)
    print(f"Generated {path}")

def generate_edge_encoding_gbk():
    """GBK encoding, Chinese headers, Special chars"""
    df = pd.DataFrame({
        '姓名': ['张三', '李四', 'Not Known', '王五'],
        'Age': [25, 30, np.nan, 40],
        '备注': ['正常', 'Test@#$%', '空行', None]
    })
    path = DATA_DIR / "edge_encoding_gbk.csv"
    try:
        df.to_csv(path, index=False, encoding='gbk')
        print(f"Generated {path} (GBK)")
    except Exception as e:
        print(f"Failed to write GBK: {e}")

def generate_stress_set():
    """50k rows x 100 cols"""
    print("Generating Stress Set (may take a moment)...")
    np.random.seed(42)
    rows = 50000
    cols = 100
    data = np.random.rand(rows, cols)
    columns = [f"col_{i}" for i in range(cols)]
    df = pd.DataFrame(data, columns=columns)
    path = DATA_DIR / "stress_50k.csv"
    df.to_csv(path, index=False)
    print(f"Generated {path} ({rows}x{cols})")

if __name__ == "__main__":
    generate_benchmark_cox()
    generate_benchmark_logistic()
    generate_edge_singular()
    generate_edge_encoding_gbk()
    generate_stress_set()
