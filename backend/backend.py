import os
import glob
from lxml import etree
from flask import Flask, jsonify, abort, request
from flask_cors import CORS
from archetype_parser import parse_archetype_to_form
import psycopg2
import json
from werkzeug.exceptions import HTTPException

ARCHETYPE_ROOT_DIR = '../openEHR_xml'

app = Flask(__name__)
CORS(app)

# --- Database Configuration (UPDATE THIS!) ---
DB_CONFIG = {
    'host': 'localhost',
    'port':'5433',
    'database': 'OpenEHR_db',
    'user': 'postgres',
    'password': 'sreena7'
}


def get_db_connection():
    """Establishes a connection to the PostgreSQL database."""
    try:
        conn = psycopg2.connect(**DB_CONFIG)
        return conn
    except Exception as e:
        print(f"ERROR: Could not connect to database: {e}")
        return None


# ---------------------------------------------

@app.errorhandler(HTTPException)
def handle_exception(e):
    """Return JSON instead of HTML for HTTP errors."""
    response = e.get_response()
    # Replace the body with a JSON object
    response.data = json.dumps({
        "code": e.code,
        "name": e.name,
        "description": e.description,
    })
    response.content_type = "application/json"
    return response


# --- This is our simple "database" ---
ARCHETYPE_FILE_MAP = {}
ARCHETYPE_LIST_CACHE = []
MAP_BUILT = False


def parse_archetype_header(xml_file):
    # ... (parse_archetype_header function remains unchanged) ...
    """
    Parses an ADL 1.4 XML file to get its ID and human-readable name.
    """
    try:
        tree = etree.parse(xml_file)
        root = tree.getroot()
        ns = {'openEHR': 'http://schemas.openehr.org/v1'}

        archetype_id_node = root.find('.//openEHR:archetype_id/openEHR:value', namespaces=ns)
        if archetype_id_node is None or archetype_id_node.text is None:
            return None
        archetype_id = archetype_id_node.text

        concept_code = root.find('.//openEHR:concept', namespaces=ns).text

        # --- THIS IS THE FIX ---
        # Look for the @language='en' ATTRIBUTE, not an element
        name_node = root.find(
            f".//openEHR:term_definitions[@language='en']/openEHR:items[@code='{concept_code}']/openEHR:items[@id='text']",
            namespaces=ns)

        # Fallback to any language if 'en' isn't found
        if name_node is None:
            name_node = root.find(
                f".//openEHR:term_definitions/openEHR:items[@code='{concept_code}']/openEHR:items[@id='text']",
                namespaces=ns)

        name = name_node.text if (name_node is not None and name_node.text is not None) else archetype_id

        return {'id': archetype_id, 'name': name, 'file_path': xml_file}

    except Exception as e:
        print(f"Error parsing header for {xml_file}: {e}. Skipping.")
        return None


def build_archetype_map():
    # ... (build_archetype_map function remains unchanged) ...
    """
    Scans all files and builds the ID-to-FilePath map AND the list cache.
    """
    global ARCHETYPE_FILE_MAP, ARCHETYPE_LIST_CACHE, MAP_BUILT
    # --- THIS IS THE FIX ---
    # If the map is already built, just return the cached list
    if MAP_BUILT:
        return ARCHETYPE_LIST_CACHE
        # -----------------------

    print("Scanning for archetypes and building map...")
    xml_files = glob.glob(os.path.join(ARCHETYPE_ROOT_DIR, '**', '*.xml'), recursive=True)

    temp_list = []
    for f in xml_files:
        header_data = parse_archetype_header(f)
        if header_data:
            ARCHETYPE_FILE_MAP[header_data['id']] = header_data['file_path']
            temp_list.append({
                'id': header_data['id'],
                'name': header_data['name']
            })

    temp_list.sort(key=lambda x: x['name'])

    ARCHETYPE_LIST_CACHE = temp_list  # <-- Save the list to the cache
    MAP_BUILT = True

    return ARCHETYPE_LIST_CACHE  # <-- Return the list


# --- API ENDPOINT 1: THE SEARCH LIST ---
@app.route('/api/archetypes', methods=['GET'])
def get_archetype_list():
    # ... (get_archetype_list function remains unchanged) ...
    """
    API Endpoint: Returns a list of all available archetypes.
    """
    archetypes_list = build_archetype_map()  # This will now always return a list
    return jsonify(archetypes_list)


# --- API ENDPOINT 2: THE FORM GENERATOR ---
@app.route('/api/archetype/form/<string:archetype_id>', methods=['GET'])
def get_archetype_form(archetype_id):
    # ... (get_archetype_form function remains unchanged) ...
    """
    API Endpoint: Returns the form structure for a single archetype.
    """
    if not MAP_BUILT:
        build_archetype_map()

    file_path = ARCHETYPE_FILE_MAP.get(archetype_id)

    if not file_path:
        print(f"Form requested for unknown ID: {archetype_id}")
        abort(404, description="Archetype ID not found.")

    print(f"Generating form for: {archetype_id} from {file_path}")

    try:
        form_fields = parse_archetype_to_form(file_path)

        if not form_fields:
            abort(404, description="Could not parse form fields for this archetype.")

        return jsonify(form_fields)

    except Exception as e:
        print(f"Critical error parsing {file_path}: {e}")
        abort(500, description="Server error while parsing archetype.")


# --- API ENDPOINT 3: SAVE TO DATABASE (NEW) ---
@app.route('/api/ehr/save', methods=['POST'])
def save_ehr_document():
    """
    API Endpoint: Receives form data and saves it to the ehr_documents table.
    """
    if not request.json:
        abort(400, description="Missing JSON data.")

    form_data = request.json

    # 1. Extract required metadata
    # These keys are sent by the frontend's handleSubmit function
    archetype_id = form_data.get('archetypeId')
    patient_id = form_data.get('patientId')

    if not archetype_id or not patient_id:
        abort(400, description="Missing 'archetypeId' or 'patientId' in form data.")

    # 2. Connect to DB
    conn = get_db_connection()
    if conn is None:
        abort(500, description="Database connection failed. Check backend console.")

    try:
        cur = conn.cursor()

        # SQL to insert data into the ehr_documents table
        insert_query = """
                       INSERT INTO ehr_documents (archetype_id, patient_id, data)
                       VALUES (%s, %s, %s) RETURNING id; \
                       """

        # Convert Python dict to a JSON string for PostgreSQL, which it converts to JSONB
        json_data_str = json.dumps(form_data)

        cur.execute(insert_query, (archetype_id, patient_id, json_data_str))

        saved_id = cur.fetchone()[0]
        conn.commit()
        cur.close()
        conn.close()

        print(f"Successfully saved document {archetype_id} for {patient_id}. DB ID: {saved_id}")

        return jsonify({
            'status': 'success',
            'message': 'Document saved successfully',
            'record_id': saved_id,
            'archetype_id': archetype_id
        }), 201

    except Exception as e:
        conn.rollback()  # Important: Rollback on error
        print(f"Database insertion error: {e}")
        abort(500, description=f"Failed to save document to database: {e}")
    finally:
        if conn:
            conn.close()


# --- Run the App ---
if __name__ == '__main__':
    print(f"Starting backend server on http://127.0.0.1:9000")
    app.run(debug=True, port=9000)