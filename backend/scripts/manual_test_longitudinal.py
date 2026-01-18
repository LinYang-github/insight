import sys
import os
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), '../')))

import requests
import pandas as pd
import numpy as np
import os
import json

BASE_URL = "http://127.0.0.1:5000/api"
PROJECT_NAME = "Longitudinal_Test_Project"
DATA_FILENAME = "longitudinal_test_data.csv"

def get_token():
    # Login as admin
    res = requests.post(f"{BASE_URL}/auth/login", json={
        "username": "admin",
        "password": "admin123"
    })
    if res.status_code != 200:
        raise Exception(f"Login failed: {res.text}")
    print("Login successful.")
    return res.json()['token']

def create_project(token):
    # Check current projects
    headers = {"Authorization": f"Bearer {token}"}
    res = requests.get(f"{BASE_URL}/projects/", headers=headers)
    projects = res.json()
    for p in projects:
        if p['name'] == PROJECT_NAME:
            print(f"Project found: {p['id']}")
            return p['id']
            
    # Create new
    res = requests.post(f"{BASE_URL}/projects/", json={
        "name": PROJECT_NAME,
        "description": "Test"
    }, headers=headers)
    print("Project created.")
    return res.json()['id']

def create_dataset(token, project_id):
    # Generate CSV
    # ID, Time, Outcome (eGFR), Age, Group
    # 50 patients, 5 visits each
    ids = []
    times = []
    outcomes = []
    ages = []
    groups = []
    
    for i in range(1, 51):
        # 3 groups: Stable (slope=0), Slow Decline (-2), Rapid Decline (-5)
        g = np.random.choice(['Stable', 'Slow', 'Rapid'])
        slope = -5 if g == 'Rapid' else (-2 if g == 'Slow' else 0)
        intercept = 90 + np.random.randn() * 10
        age = 60 + np.random.randn() * 10
        
        for t in range(5):
            ids.append(i)
            times.append(t)
            # outcome = intercept + slope*t + random_noise
            y = intercept + slope * t + np.random.randn() * 2
            outcomes.append(y)
            ages.append(age)
            groups.append(g)
            
    df = pd.DataFrame({
        'ID': ids,
        'Time': times,
        'eGFR': outcomes,
        'Age': ages,
        'Group': groups
    })
    
    path = f"backend/data/{DATA_FILENAME}"
    os.makedirs("backend/data", exist_ok=True)
    df.to_csv(path, index=False)
    print(f"Data generated at {path}")
    
    # Upload (simulate upload by placing file and calling create dataset)
    # Actually API expects file upload. For simplicity in verification script,
    # we can use the /data/upload endpoints or better, just manually insert if we had access.
    # But let's use the API properly.
    
    files = {'file': open(path, 'rb')}
    headers = {"Authorization": f"Bearer {token}"}
    res = requests.post(f"{BASE_URL}/data/upload/{project_id}", files=files, headers=headers)
    if res.status_code != 201:
        raise Exception(f"Upload failed: {res.text}")
        
    print("Dataset uploaded.")
    return res.json()['dataset_id']

def run_lmm(token, dataset_id):
    print("\n--- Testing LMM ---")
    headers = {"Authorization": f"Bearer {token}"}
    payload = {
        "dataset_id": dataset_id,
        "id_col": "ID",
        "time_col": "Time",
        "outcome_col": "eGFR",
        "fixed_effects": ["Age", "Group"]
    }
    res = requests.post(f"{BASE_URL}/longitudinal/lmm", json=payload, headers=headers)
    if res.status_code == 200:
        print("LMM Success!")
        # print(json.dumps(res.json()['results']['summary'], indent=2))
        return True
    else:
        print(f"LMM Failed: {res.text}")
        return False

def run_clustering(token, dataset_id):
    print("\n--- Testing Clustering ---")
    headers = {"Authorization": f"Bearer {token}"}
    payload = {
        "dataset_id": dataset_id,
        "id_col": "ID",
        "time_col": "Time",
        "outcome_col": "eGFR",
        "n_clusters": 3
    }
    res = requests.post(f"{BASE_URL}/longitudinal/clustering", json=payload, headers=headers)
    
    if res.status_code == 200:
        print("Clustering Success!")
        # Check centroids
        cents = res.json()['results']['centroids']
        print("Centroids:", cents)
        return True
    else:
        print(f"Clustering Failed: {res.text}")
        return False

def run_variability(token, dataset_id):
    print("\n--- Testing Variability ---")
    headers = {"Authorization": f"Bearer {token}"}
    payload = {
        "dataset_id": dataset_id,
        "id_col": "ID",
        "outcome_col": "eGFR"
    }
    res = requests.post(f"{BASE_URL}/longitudinal/variability", json=payload, headers=headers)
    
    if res.status_code == 200:
        print("Variability Success!")
        return True
    else:
        print(f"Variability Failed: {res.text}")
        return False

if __name__ == "__main__":
    try:
        token = get_token()
        pid = create_project(token)
        did = create_dataset(token, pid)
        
        success = True
        success &= run_lmm(token, did)
        success &= run_clustering(token, did)
        success &= run_variability(token, did)
        
        if success:
            print("\nAll Longitudinal Tests Passed.")
        else:
            print("\nSome Tests Failed.")
            exit(1)
    except Exception as e:
        print(f"\nError: {e}")
        exit(1)