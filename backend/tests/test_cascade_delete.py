
import pytest
from app import create_app, db
from app.models.dataset import Dataset
from app.models.project import Project
from app.models.user import User

class TestConfig:
    TESTING = True
    SQLALCHEMY_DATABASE_URI = "sqlite:///:memory:"
    SQLALCHEMY_TRACK_MODIFICATIONS = False

@pytest.fixture
def app_context():
    app = create_app(config_class=TestConfig)
    
    with app.app_context():
        db.create_all()
        
        # Setup User & Project
        user = User(username='test_cascade', email='cascade@test.com')
        db.session.add(user)
        db.session.commit()
        project = Project(name='Cascade Project', author=user)
        db.session.add(project)
        db.session.commit()
        
        yield app
        db.session.remove()
        db.drop_all()

def test_cascade_delete_children(app_context):
    """
    Test that deleting a parent dataset deletes its children (derived datasets).
    Model definition: parent = db.relationship(..., backref=db.backref('children', cascade="all, delete-orphan"))
    Wait, let's check the model definition in dataset.py first.
    """
    # Create Parent
    parent = Dataset(name="parent.csv", project_id=1)
    db.session.add(parent)
    db.session.commit()
    
    # Create Child
    child = Dataset(name="child.csv", project_id=1, parent_id=parent.id)
    db.session.add(child)
    db.session.commit()
    
    assert Dataset.query.count() == 2
    
    # Delete Parent
    db.session.delete(parent)
    db.session.commit()
    
    # Assert Child is gone
    assert Dataset.query.get(child.id) is None
    assert Dataset.query.count() == 0
    print("Cascade delete successful!")
