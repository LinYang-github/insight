import requests
import json

BASE_URL = 'http://127.0.0.1:5000/api'

def test_flow():
    # 1. Register
    print("Registering...")
    email = "test@example.com"
    username = "testuser"
    password = "password123"
    
    # Clean up if possible or ignore error
    
    resp = requests.post(f"{BASE_URL}/auth/register", json={
        "username": username,
        "email": email,
        "password": password
    })
    print("Register:", resp.status_code)
    if not resp.ok:
        print("Error:", resp.text)
        return
    print(resp.json())

    # 2. Login
    print("Logging in...")
    resp = requests.post(f"{BASE_URL}/auth/login", json={
        "username": username,
        "password": password
    })
    print("Login:", resp.status_code)
    if resp.status_code != 200:
        return
    token = resp.json()['token']
    headers = {"Authorization": f"Bearer {token}"}

    # 3. Create Project
    print("Creating Project...")
    resp = requests.post(f"{BASE_URL}/projects/", headers=headers, json={
        "name": "Test Project",
        "description": "A test project"
    })
    print("Create Project:", resp.status_code, resp.json())
    project_id = resp.json().get('id')

    # 4. Upload File
    if project_id:
        print("Uploading File...")
        # Create a dummy csv
        with open("test_data.csv", "w") as f:
            f.write("age,sex,outcome\n25,M,0\n30,F,1\n")
            
        files = {'file': open('test_data.csv', 'rb')}
        resp = requests.post(f"{BASE_URL}/data/upload/{project_id}", headers=headers, files=files)
        print("Upload:", resp.status_code, resp.json())

if __name__ == "__main__":
    test_flow()
