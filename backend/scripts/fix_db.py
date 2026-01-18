import sys
import os
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), '../')))

import sqlite3
import os

db_path = 'backend/insight.db'
if not os.path.exists(db_path):
    print(f"DB not found at {db_path}")
    exit(1)

conn = sqlite3.connect(db_path)
c = conn.cursor()

columns = [
    ("parent_id", "INTEGER"),
    ("action_type", "VARCHAR(32)"),
    ("action_log", "TEXT")
]

for col, dtype in columns:
    try:
        print(f"Adding {col}...")
        c.execute(f"ALTER TABLE dataset ADD COLUMN {col} {dtype};")
        print("Success.")
    except Exception as e:
        print(f"Failed to add {col}: {e}")

conn.commit()
conn.close()
print("Schema patch completed.")