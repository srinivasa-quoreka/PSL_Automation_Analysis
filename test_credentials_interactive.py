#!/usr/bin/env python
"""
Manual Jira Authentication Test
Run this to verify your credentials are correct.
"""

import requests
from requests.auth import HTTPBasicAuth
import urllib3

urllib3.disable_warnings()

print("=" * 60)
print("JIRA AUTHENTICATION TEST")
print("=" * 60)

username = input("Enter Jira Username: ").strip()
password = input("Enter Jira Password: ").strip()
base_url = input("Enter Jira Base URL (e.g., https://jira.ekaplus.com): ").strip().rstrip("/")

print(f"\nTesting with:")
print(f"  URL: {base_url}")
print(f"  Username: {username}")
print(f"  Password: {'*' * len(password)}")
print()

auth = HTTPBasicAuth(username, password)
test_url = f"{base_url}/rest/api/2/myself"

try:
    print(f"Connecting to {test_url}...")
    r = requests.get(test_url, auth=auth, timeout=10, verify=False)
    
    print(f"Status: {r.status_code}")
    
    if r.status_code == 200:
        print("✓ SUCCESS - Authentication works!")
        user = r.json()
        print(f"  Logged in as: {user.get('displayName', user.get('name'))}")
        print(f"  Email: {user.get('emailAddress', 'N/A')}")
    else:
        print(f"✗ FAILED - {r.status_code}")
        print(f"  Response: {r.text[:300]}")
        
except Exception as e:
    print(f"✗ ERROR: {e}")

print("\n" + "=" * 60)
