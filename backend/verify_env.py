import os
import sys

def check_import(module_name):
    try:
        __import__(module_name)
        print(f"[OK] {module_name} is installed.")
    except ImportError:
        print(f"[MISSING] {module_name} is NOT installed.")

print("Checking dependencies...")
check_import('flask')
check_import('flask_cors')
check_import('lxml')
check_import('psycopg2')
check_import('werkzeug')

print("\nChecking directories...")
archetype_dir = os.path.join('..', 'openEHR_xml')
if os.path.exists(archetype_dir):
    print(f"[OK] Directory {archetype_dir} exists.")
else:
    print(f"[MISSING] Directory {archetype_dir} does NOT exist.")
