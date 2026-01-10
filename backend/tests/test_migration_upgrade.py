
import pytest
from app import create_app, db
from sqlalchemy import text
from flask_migrate import upgrade, downgrade
import os

@pytest.fixture
def app_with_legacy_db(tmp_path):
    """
    Creates an app instance using a real SQLite file initialized with the OLD schema (no lineage columns).
    """
    db_path = tmp_path / "legacy.db"
    app = create_app()
    app.config['SQLALCHEMY_DATABASE_URI'] = f"sqlite:///{db_path}"
    app.config['TESTING'] = True
    
    with app.app_context():
        # Manually create the OLD table structure (before migration)
        with db.engine.connect() as conn:
            conn.execute(text("""
                CREATE TABLE project (
                    id INTEGER NOT NULL, 
                    name VARCHAR(128), 
                    description TEXT, 
                    created_at DATETIME, 
                    user_id INTEGER, 
                    active_dataset_id INTEGER, 
                    PRIMARY KEY (id)
                );
            """))
            conn.execute(text("""
                CREATE TABLE user (
                    id INTEGER NOT NULL, 
                    username VARCHAR(64), 
                    email VARCHAR(120), 
                    password_hash VARCHAR(128), 
                    settings JSON, 
                    PRIMARY KEY (id)
                );
            """))
            conn.execute(text("""
                CREATE TABLE dataset (
                    id INTEGER NOT NULL, 
                    project_id INTEGER NOT NULL, 
                    name VARCHAR(128), 
                    filepath VARCHAR(512), 
                    created_at DATETIME, 
                    metadata TEXT, 
                    PRIMARY KEY (id),
                    FOREIGN KEY(project_id) REFERENCES project (id)
                );
            """))
            conn.commit()
            
        yield app

def test_migration_adds_lineage_columns(app_with_legacy_db):
    """
    Test that applying the migration adds 'parent_id' and related columns to an existing 'dataset' table.
    """
    app = app_with_legacy_db
    
    with app.app_context():
        # Verify columns MISSING before upgrade
        with db.engine.connect() as conn:
            result = conn.execute(text("PRAGMA table_info(dataset)"))
            columns = [row.name for row in result]
            assert 'parent_id' not in columns
            assert 'action_type' not in columns
        
        # Apply Upgrade
        # Note: We need to point to the migrations directory
        migrations_dir = os.path.join(os.path.dirname(os.path.dirname(__file__)), 'migrations')
        upgrade(directory=migrations_dir)
        
        # Verify columns EXIST after upgrade
        with db.engine.connect() as conn:
            result = conn.execute(text("PRAGMA table_info(dataset)"))
            columns = [row.name for row in result]
            
            assert 'parent_id' in columns
            assert 'action_type' in columns
            assert 'action_log' in columns
            
            # Verify data preservation (optional, if we inserted data)
            print("Migration successful! Lineage columns added.")
