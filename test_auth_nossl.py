import requests
from requests.auth import HTTPBasicAuth
import urllib3

# Disable SSL warnings
urllib3.disable_warnings(urllib3.exceptions.InsecureRequestWarning)

# Test direct Jira API call WITHOUT SSL verification
url = 'https://jira.ekaplus.com/rest/api/2/myself'
auth = HTTPBasicAuth('sriniva.a@ekaplus.com', 'Sree@10904')

try:
    r = requests.get(url, auth=auth, timeout=10, verify=False)
    print(f'Status: {r.status_code}')
    if r.status_code == 200:
        print('✓ Authentication successful!')
        user = r.json()
        print(f'Logged in as: {user.get("name")}')
    else:
        print(f'Error: {r.status_code}')
        print(f'Response: {r.text[:200]}')
except Exception as e:
    print(f'Connection error: {e}')
