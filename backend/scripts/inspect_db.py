
from app import create_app, db
from sqlalchemy import text

app = create_app()

with app.app_context():
    print(f"DB URI: {app.config['SQLALCHEMY_DATABASE_URI']}")
    
    try:
        # Check table info
        with db.engine.connect() as conn:
            # List all tables
            result = conn.execute(text("SELECT name FROM sqlite_master WHERE type='table';"))
            tables = [row[0] for row in result]
            print(f"All tables: {tables}")
            
            if 'dataset' in tables:
                print("Table 'dataset' FOUND.")
                result = conn.execute(text("PRAGMA table_info(dataset)"))
                columns = [row.name for row in result]
                print(f"Columns in dataset: {columns}")
            else:
                print("Table 'dataset' NOT FOUND.")
                
            # Check alembic version
            result = conn.execute(text("SELECT * FROM alembic_version"))
            version = result.fetchone()
            print(f"Alembic Version: {version}")
            
    except Exception as e:
        print(f"Error inspecting DB: {e}")
