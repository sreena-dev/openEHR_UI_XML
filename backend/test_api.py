import requests
import json

try:
    response = requests.get('http://127.0.0.1:9000/api/archetypes')
    print(f"Status Code: {response.status_code}")
    if response.status_code == 200:
        data = response.json()
        print(f"Received {len(data)} archetypes.")
        # print first 2 to verify structure
        print(json.dumps(data[:2], indent=2))
    else:
        print(f"Error: {response.text}")
except Exception as e:
    print(f"Request failed: {e}")
