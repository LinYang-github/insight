import requests
import sys

BASE_URL = 'http://127.0.0.1:5000'

def test_static_serving():
    try:
        # 1. Test Root
        resp = requests.get(BASE_URL)
        print(f"GET / status: {resp.status_code}")
        if resp.status_code != 200:
            print(f"Error: {resp.text}")
            sys.exit(1)
        
        if '<!doctype html>' not in resp.text.lower():
            print("Error: Root did not return HTML")
            print(resp.text[:100])
            sys.exit(1)
            
        print("Root serving HTML: OK")

        # 2. Test SPA Route (should return index.html)
        resp = requests.get(f"{BASE_URL}/some/random/route")
        print(f"GET /some/random/route status: {resp.status_code}")
        if resp.status_code != 200:
             print("Error: SPA route failed")
             sys.exit(1)
        
        if '<!doctype html>' not in resp.text.lower():
             print("Error: SPA route did not return HTML")
             sys.exit(1)
             
        print("SPA Route: OK")

        # 3. Test API (should NOT return HTML)
        resp = requests.get(f"{BASE_URL}/api/projects")
        # Should be 401 Unauthorized (json), not 200 HTML
        print(f"GET /api/projects status: {resp.status_code}")
        if resp.status_code != 401:
             print(f"Error: API route returned {resp.status_code}")
             # check if content type is json
        
        if 'application/json' not in resp.headers.get('Content-Type', ''):
             print("Error: API route did not return JSON")
             sys.exit(1)
             
        print("API Route protection: OK")
        
    except Exception as e:
        print(f"Exception: {e}")
        sys.exit(1)

if __name__ == "__main__":
    test_static_serving()
