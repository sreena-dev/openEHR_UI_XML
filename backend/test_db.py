import sys
from db import save_patient_ehr_link, get_ehr_id_for_patient
from uuid import uuid4

def test_db():
    print("Testing DB Patient Mapping...")
    
    test_patient = "PAT_TEST_123"
    test_ehr = str(uuid4())
    
    # Test Save
    print(f"Saving mapping: {test_patient} -> {test_ehr}")
    save_result = save_patient_ehr_link(test_patient, test_ehr)
    if not save_result:
        print("❌ Failed to save map")
        sys.exit(1)
        
    print("✅ Save successful")
        
    # Test Retrieve
    fetched = get_ehr_id_for_patient(test_patient)
    print(f"Fetched mapping: {test_patient} -> {fetched}")
    
    if str(fetched) == test_ehr:
        print("✅ Retrieve successful and match")
    else:
        print(f"❌ Mismatch. Expected {test_ehr}, got {fetched}")
        sys.exit(1)

if __name__ == "__main__":
    test_db()
