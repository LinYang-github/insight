
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
