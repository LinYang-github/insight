
import pytest
from app import create_app, db
from app.config import TestConfig

@pytest.fixture
def app():
    app = create_app(TestConfig)
    
    # Push context
    ctx = app.app_context()
    ctx.push()
    
    yield app
    
    ctx.pop()

@pytest.fixture
def client(app):
    return app.test_client()

@pytest.fixture
def runner(app):
    return app.test_cli_runner()

@pytest.fixture(autouse=True)
def db_setup(app):
    """
    Ensure a clean database for each test.
    """
    db.create_all()
    yield
    db.session.remove()
    db.drop_all()

@pytest.fixture
def golden_data_path():
    """Returns the path to the golden test data directory."""
    import os
    return os.path.join(os.path.dirname(__file__), 'test_data')

@pytest.fixture
def load_golden_dataset(golden_data_path):
    """Helper to load a CSV from golden data directory."""
    import pandas as pd
    import os
    def _load(filename, **kwargs):
        path = os.path.join(golden_data_path, filename)
        if not os.path.exists(path):
            pytest.skip(f"Golden dataset {filename} not found.")
        return pd.read_csv(path, **kwargs)
    return _load
