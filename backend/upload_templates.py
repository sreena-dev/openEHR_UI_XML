import os
import requests
from dotenv import load_dotenv

# Load environment variables
load_dotenv()

BASE_URL = os.getenv('EHRBASE_BASE_URL', 'http://localhost:8080/ehrbase')
USER = os.getenv('EHRBASE_USER', 'admin')
PASSWORD = os.getenv('EHRBASE_PASSWORD', 'password')

def upload_templates(template_dir):
    """
    Scans a directory for .opt files and uploads them to EHRbase.
    """
    if not os.path.exists(template_dir):
        print(f"Error: Directory {template_dir} does not exist.")
        return

    # Endpoint for ADL 1.4 template upload
    upload_url = f"{BASE_URL}/rest/openehr/v1/definition/template/adl1.4"
    
    auth = (USER, PASSWORD)
    headers = {
        'Content-Type': 'application/xml',
        'Accept': 'application/xml'
    }

    print(f"Scanning for .opt files in: {template_dir}")
    count = 0
    success = 0

    files = [f for f in os.listdir(template_dir) if f.endswith('.opt')]
    
    for filename in files:
        count += 1
        file_path = os.path.join(template_dir, filename)
        
        with open(file_path, 'rb') as f:
            xml_data = f.read()

        print(f"Uploading {filename}...")
        try:
            response = requests.post(upload_url, data=xml_data, auth=auth, headers=headers)

            if response.status_code in [201, 204]:
                print(f"✅ Successfully uploaded {filename}")
                success += 1
            elif response.status_code == 409:
                print(f"⚠️ {filename} already exists in EHRbase.")
                success += 1 # Count as success since it's already there
            else:
                print(f"❌ Failed to upload {filename}. Status: {response.status_code}")
                # print(f"   Response: {response.text[:200]}")
        except Exception as e:
            print(f"❌ Error uploading {filename}: {str(e)}")

    print("-" * 30)
    print(f"Summary: Found {count} .opt files. {success} templates ready in EHRbase.")

if __name__ == "__main__":
    # Upload from the specific folder we downloaded to
    UPLOAD_DIR = os.path.join(os.path.dirname(__file__), "opt_upload_folder")
    upload_templates(UPLOAD_DIR)
