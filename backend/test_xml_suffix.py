import requests

archetype_id = "openEHR-EHR-CLUSTER.blood_cell_count.v0.xml"
url = f"http://127.0.0.1:9000/api/archetype/form/{archetype_id}"

print(f"Testing URL: {url}")

try:
    response = requests.get(url)
    print(f"Status Code: {response.status_code}")
    if response.status_code == 200:
        print("Success!")
    else:
        print(f"Error: {response.text}")
except Exception as e:
    print(f"Request failed: {e}")
