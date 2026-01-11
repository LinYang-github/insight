
import pytest
from app import create_app, db
from app.models.dataset import Dataset
from sqlalchemy import text

from app.config import TestConfig

@pytest.fixture
def app_context():
    app = create_app(TestConfig)
    with app.app_context():
        db.create_all()
        yield app
        db.session.remove()
        db.drop_all()

def test_lineage_columns_exist(app_context):
    """
    Verify parent_id, action_type, action_log columns exist in the DB schema.
    """
    with db.engine.connect() as conn:
        result = conn.execute(text("PRAGMA table_info(dataset)"))
        columns = [row.name for row in result]
        
        assert 'parent_id' in columns
        assert 'action_type' in columns
        assert 'action_log' in columns

def test_lineage_relationship(app_context):
    """
    Verify parent/child relationship behavior.
    """
    # Create Parent
    parent = Dataset(name="parent.csv", filepath="/tmp/parent.csv", project_id=1)
    db.session.add(parent)
    db.session.commit()
    
    # Create Child
    child = Dataset(name="child.csv", filepath="/tmp/child.csv", project_id=1, parent_id=parent.id, action_type="impute")
    db.session.add(child)
    db.session.commit()
    
    # Fetch
    fetched_parent = Dataset.query.get(parent.id)
    fetched_child = Dataset.query.get(child.id)
    
    # Check assertions
    assert fetched_child.parent_id == fetched_parent.id
    assert fetched_child.parent == fetched_parent
    assert fetched_child in fetched_parent.children
    assert fetched_child.action_type == "impute"
