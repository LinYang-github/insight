
import pytest
from app import create_app, db
from app.models.user import User
from app.models.project import Project

class TestConfig:
    TESTING = True
    SQLALCHEMY_DATABASE_URI = "sqlite:///:memory:"
    SQLALCHEMY_TRACK_MODIFICATIONS = False
    SECRET_KEY = "test_key"

@pytest.fixture
def test_setup():
    app = create_app(config_class=TestConfig)
    with app.app_context():
        db.create_all()
        
        # User A
        user_a = User(username='user_a', email='a@test.com')
        db.session.add(user_a)
        
        # User B
        user_b = User(username='user_b', email='b@test.com')
        db.session.add(user_b)
        
        db.session.commit()
        
        # Project A (owned by A)
        proj_a = Project(name='Project A', author=user_a)
        db.session.add(proj_a)
        
        # Project B (owned by B)
        proj_b = Project(name='Project B', author=user_b)
        db.session.add(proj_b)
        
        db.session.commit()
        
        yield app, user_a, user_b, proj_a, proj_b

def test_project_isolation(test_setup):
    app, user_a, user_b, proj_a, proj_b = test_setup
    
    with app.test_client() as client:
        # Mock Login for User A
        # Since we use `current_user` from token, we need to generate tokens.
        # But for unit test of logic, we can also test the Service/Query logic or API via token.
        # Let's use API with token mock.
        import jwt
        import datetime
        from app.config import Config
        
        token_a = jwt.encode({'user_id': user_a.id, 'exp': datetime.datetime.utcnow() + datetime.timedelta(hours=1)}, Config.SECRET_KEY, algorithm='HS256')
        token_b = jwt.encode({'user_id': user_b.id, 'exp': datetime.datetime.utcnow() + datetime.timedelta(hours=1)}, Config.SECRET_KEY, algorithm='HS256')
        
        # 1. User A should see Project A
        res_a = client.get('/api/projects/', headers={'Authorization': f'Bearer {token_a}'})
        projects_a = res_a.get_json()['projects']
        assert len(projects_a) == 1
        assert projects_a[0]['name'] == 'Project A'
        
        # 2. User A should NOT see Project B
        # (Implicitly verified by len=1, but let's check IDs)
        assert projects_a[0]['id'] == proj_a.id
        
        # 3. User A try to access Project B -> 403
        res_access = client.get(f'/api/projects/{proj_b.id}', headers={'Authorization': f'Bearer {token_a}'})
        assert res_access.status_code == 403
        assert 'Permission denied' in res_access.get_json()['message']
        
        print("Isolation Verification Passed!")

if __name__ == "__main__":
    pass
