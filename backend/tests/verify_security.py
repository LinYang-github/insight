
import pytest
from app import create_app, db
from app.models.user import User

class TestConfig:
    TESTING = True
    SQLALCHEMY_DATABASE_URI = "sqlite:///:memory:"
    SQLALCHEMY_TRACK_MODIFICATIONS = False
    SECRET_KEY = "test_secret"

@pytest.fixture
def client():
    app = create_app(config_class=TestConfig)
    with app.app_context():
        db.create_all()
        yield app.test_client()

def test_protected_endpoint_no_token(client):
    """Accessing protected endpoint without token should fail."""
    # Try accessing table1 generation
    response = client.post('/api/statistics/table1', json={})
    assert response.status_code == 401
    assert 'Token is missing' in response.get_json()['message']

def test_protected_endpoint_invalid_token(client):
    """Accessing protected endpoint with bad token should fail."""
    response = client.post('/api/statistics/table1', json={}, headers={'Authorization': 'Bearer invalid_token'})
    assert response.status_code == 401
    assert 'Token is invalid' in response.get_json()['message']

def test_valid_login_flow(client):
    """Full flow: Login -> Get Token -> Access Protected Endpoint."""
    # 1. Register/Create User (Manual DB insert for speed)
    from werkzeug.security import generate_password_hash
    with client.application.app_context():
        u = User(username='hacker', email='h@hack.com', password_hash=generate_password_hash('123456'))
        db.session.add(u)
        db.session.commit()
    
    # 2. Login
    login_res = client.post('/api/auth/login', json={'username': 'hacker', 'password': '123456'})
    assert login_res.status_code == 200
    token = login_res.get_json()['token']
    assert token is not None
    
    # 3. Access Protected (Expect 400 Bad Request because missing args, NOT 401 Unauthorized)
    protected_res = client.post('/api/statistics/table1', 
                                json={}, # Missing args, should trigger 400 validation error
                                headers={'Authorization': f'Bearer {token}'})
    
    assert protected_res.status_code == 400 # Proof that we passed Auth layer
    print("Security Verification Passed!")

if __name__ == "__main__":
    # Manually run via pytest usually, but allowing python execution if imports match
    pass
