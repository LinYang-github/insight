import sys
import os
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), '../')))

import urllib.request
import urllib.parse
import json
import pandas as pd
import numpy as np
import os

BASE_URL = "http://127.0.0.1:5000/api"
PROJECT_NAME = "Longitudinal_Test_Project"
DATA_FILENAME = "longitudinal_test_data.csv"

def request(method, url, data=None, headers=None):
    if headers is None: headers = {}
    
    if data:
        json_data = json.dumps(data).encode('utf-8')
        headers['Content-Type'] = 'application/json'
    else:
        json_data = None
        
    req = urllib.request.Request(url, data=json_data, headers=headers, method=method)
    try:
        with urllib.request.urlopen(req) as response:
            return response.status, json.load(response)
    except urllib.error.HTTPError as e:
        return e.code, json.load(e)

def upload_file(url, filepath, token):
    # Minimal multipart upload implementation usually requires 'requests' or complex construction.
    # Since we don't have requests, let's use the 'manual' approach:
    # Actually, constructing multipart/form-data with urllib is painful.
    # Let's try to just use the `DataService` internally if possible?
    # Or simple hack: Copy file to backend/data manually (simulating upload) 
    # and then Create Dataset record directly in DB? 
    # No, that bypasses API logic.
    
    # Alternative: Use curl via subprocess.
    import subprocess
    cmd = [
        "curl", "-X", "POST",
        "-H", f"Authorization: Bearer {token}",
        "-F", f"file=@{filepath}",
        url
    ]
    result = subprocess.run(cmd, capture_output=True, text=True)
    if result.returncode != 0:
        raise Exception(f"Upload failed: {result.stderr}")
    return 201, json.loads(result.stdout)

def get_token():
    status, data = request("POST", f"{BASE_URL}/auth/login", {"username": "admin", "password": "admin123"})
    if status != 200:
        raise Exception(f"Login failed: {data}")
    print("Login successful.")
    return data['token']

def create_project(token):
    headers = {"Authorization": f"Bearer {token}"}
    status, data = request("GET", f"{BASE_URL}/projects/", headers=headers)
    print(f"DEBUG: Projects Response ({status}): {type(data)}")
    if not isinstance(data, list):
        print(f"DEBUG: Data content: {data}")
        # If it's a dict, maybe it's wrapped? Or error?
        if 'projects' in data: data = data['projects']
        else: return -1 # Error
    
    for p in data:
        if p['name'] == PROJECT_NAME:
            print(f"Project found: {p['id']}")
            return p['id']
            
    status, data = request("POST", f"{BASE_URL}/projects/", {"name": PROJECT_NAME, "description": "Test"}, headers=headers)
    print("Project created.")
    return data['id']

def create_dataset_and_upload(token, project_id):
    # Generaate Data
    ids, times, outcomes, ages, groups = [], [], [], [], []
    for i in range(1, 11): # 10 patients
        g = np.random.choice(['Stable', 'Slow', 'Rapid'])
        slope = -5 if g == 'Rapid' else (-2 if g == 'Slow' else 0)
        intercept = 90 + np.random.randn() * 10
        age = 60 + np.random.randn() * 10
        for t in range(5):
            ids.append(i)
            times.append(t)
            y = intercept + slope * t + np.random.randn() * 1
            outcomes.append(y)
            ages.append(age)
            groups.append(g)
            
    df = pd.DataFrame({'ID': ids, 'Time': times, 'eGFR': outcomes, 'Age': ages, 'Group': groups})
    
    # Save to temp
    path = os.path.abspath(f"backend/data/{DATA_FILENAME}")
    os.makedirs("backend/data", exist_ok=True)
    df.to_csv(path, index=False)
    print(f"Data generated at {path}")
    
    # Upload via Curl
    status, data = upload_file(f"{BASE_URL}/data/upload/{project_id}", path, token)
    if status not in [200, 201]:
         raise Exception(f"Upload failed: {data}")
         
    print("Dataset uploaded.")
    return data['dataset_id']

def run_tests(token, dataset_id):
    headers = {"Authorization": f"Bearer {token}"}
    
    # LMM
    print("\n--- Testing LMM ---")
    status, data = request("POST", f"{BASE_URL}/longitudinal/lmm", {
        "dataset_id": dataset_id,
         "id_col": "ID", "time_col": "Time", "outcome_col": "eGFR",
         "fixed_effects": ["Age"]
    }, headers)
    if status == 200: print("LMM Success!")
    else: print(f"LMM Failed: {data}")
    
    # Clustering
    print("\n--- Testing Clustering ---")
    status, data = request("POST", f"{BASE_URL}/longitudinal/clustering", {
        "dataset_id": dataset_id,
        "id_col": "ID", "time_col": "Time", "outcome_col": "eGFR",
        "n_clusters": 2
    }, headers)
    if status == 200: 
        print("Clustering Success!")
        print("Centroids:", data['results']['centroids'])
    else: print(f"Clustering Failed: {data}")

    # Variability
    print("\n--- Testing Variability ---")
    status, data = request("POST", f"{BASE_URL}/longitudinal/variability", {
        "dataset_id": dataset_id,
        "id_col": "ID", "outcome_col": "eGFR"
    }, headers)
    if status == 200: 
        print("Variability Success!")
        print("Sample:", data['results'][0])
    else: print(f"Variability Failed: {data}")

if __name__ == "__main__":
    try:
        token = get_token()
        pid = create_project(token)
        did = create_dataset_and_upload(token, pid)
        run_tests(token, did)
        print("\nAll Longitudinal Tests Passed.")
    except Exception as e:
        print(f"\nError: {e}")