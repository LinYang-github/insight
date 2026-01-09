
import pytest
import io
import json

def test_api_flow(client):
    """
    Test the full user flow: Register -> Login -> Create Project -> Upload File
    """
    # 1. Register
    email = "test@example.com"
    username = "testuser"
    password = "password123"
    
    resp = client.post("/api/auth/register", json={
        "username": username,
        "email": email,
        "password": password
    })
    assert resp.status_code == 201, f"Register failed: {resp.get_json()}"
    
    # 2. Login
    resp = client.post("/api/auth/login", json={
        "username": username,
        "password": password
    })
    assert resp.status_code == 200, f"Login failed: {resp.get_json()}"
    token = resp.get_json()['token']
    headers = {"Authorization": f"Bearer {token}"}
    
    # 3. Create Project
    resp = client.post("/api/projects/", headers=headers, json={
        "name": "Test Project",
        "description": "A test project"
    })
    assert resp.status_code == 201, f"Create project failed: {resp.get_json()}"
    project_id = resp.get_json().get('id')
    assert project_id is not None
    
    # 4. Upload File
    # Create in-memory CSV
    csv_content = b"age,sex,outcome\n25,M,0\n30,F,1\n"
    data = {
        'file': (io.BytesIO(csv_content), 'test_data.csv')
    }
    
    resp = client.post(f"/api/data/upload/{project_id}", headers=headers, data=data, content_type='multipart/form-data')
    assert resp.status_code == 201, f"Upload failed: {resp.get_json()}"
    
    # Verify upload metadata
    data_resp = resp.get_json()
    assert 'dataset_id' in data_resp
    assert 'variables' in data_resp['metadata']
