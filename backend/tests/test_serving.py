import pytest

def test_static_serving_root(client):
    """Test Root returns HTML"""
    resp = client.get('/', follow_redirects=True)
    assert resp.status_code == 200, f"Error: {resp.text}"
    assert b'<!doctype html>' in resp.data.lower()

def test_static_serving_spa(client):
    """Test SPA route returns index.html"""
    resp = client.get('/some/random/route', follow_redirects=True)
    assert resp.status_code == 200
    assert b'<!doctype html>' in resp.data.lower()

def test_api_protection(client):
    """Test API should not return HTML for 401"""
    # Fix: follow_redirects=True to handle /api/projects -> /api/projects/ if needed, 
    # but strictly API endpoints might not redirect. 
    # However we got 308, so likely trailing slash issue.
    # Flask default: if rule ends in /, missing slash -> 308.
    resp = client.get('/api/projects', follow_redirects=True)
    assert resp.status_code == 401
    assert resp.is_json
