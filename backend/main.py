# import os
# import glob
# from lxml import etree
# from flask import Flask, jsonify, abort, request
# from flask_cors import CORS
# import psycopg2
# import json
#
#
# DB_CONFIG = {
#     'host': 'localhost',
#     'database': 'openEHR_db',
#     'user': 'postgres',
#     'password': 'root'
# }
#
# # ... (after DB_CONFIG)
#
# def get_db_connection():
#     """Connects to the PostgreSQL database."""
#     try:
#         conn = psycopg2.connect(**DB_CONFIG)
#         return conn
#     except Exception as e:
#         print(f"ERROR: Could not connect to database: {e}")
#         # In a real app, you would raise a proper exception or log this
#         return None
#
# # ... (rest of main.py)
# # --- Config ---
# ARCHETYPE_ROOT_DIR = '../openEHR_xml'
# ARCHETYPE_CACHE = {}
# # Tell Flask to serve static files from the current directory
# app = Flask(__name__, static_url_path='', static_folder='.')
# CORS(app)  # This lets your frontend call the API
#
# # Define the XML namespaces we'll be using
# NS = {'openEHR': 'http://schemas.openehr.org/v1'}
#
#
# def parse_archetype_header(xml_file):
#     """
#     (Robust v3)
#     Parses an ADL 1.4 XML file to get its ID, name, and file path.
#     This is much more forgiving.
#     """
#     try:
#         tree = etree.parse(xml_file)
#         root = tree.getroot()
#         ns = {'openEHR': 'http://schemas.openehr.org/v1'}
#
#         # 1. Get the Archetype ID (This is mandatory)
#         archetype_id_node = root.find('.//openEHR:archetype_id/openEHR:value', namespaces=ns)
#         if archetype_id_node is None or archetype_id_node.text is None:
#             print(f"Skipping {xml_file}: Could not find <archetype_id>.")
#             return None
#
#         archetype_id = archetype_id_node.text
#         name = archetype_id  # Default name is the ID itself
#
#         # 2. Get the concept code (Optional)
#         concept_node = root.find('.//openEHR:concept', namespaces=ns)
#         if concept_node is not None and concept_node.text is not None:
#             concept_code = concept_node.text
#
#             # 3. Get the human-readable name (Optional)
#             name_node = root.find(
#                 f".//openEHR:term_definitions[@language='en']/openEHR:items[@code='{concept_code}']/openEHR:items[@id='text']",
#                 namespaces=ns)
#
#             if name_node is not None and name_node.text is not None:
#                 name = name_node.text  # Overwrite default name if found
#
#         return {
#             'id': archetype_id,
#             'name': name,
#             'path': xml_file
#         }
#
#     except etree.XMLSyntaxError:
#         print(f"XML Syntax Error parsing {xml_file}. Skipping.")
#         return None
#     except Exception as e:
#         print(f"Generic error on {xml_file}: {e}. Skipping.")
#         return None
#
#
# def build_archetype_cache():
#     """
#     Scans the directory on startup and fills the ARCHETYPE_CACHE.
#     """
#     print("Building archetype cache...")
#     xml_files = glob.glob(os.path.join(ARCHETYPE_ROOT_DIR, '**', '*.xml'), recursive=True)
#
#     parsed_count = 0
#     for f in xml_files:
#         header_data = parse_archetype_header(f)
#         if header_data:
#             ARCHETYPE_CACHE[header_data['id']] = header_data
#             parsed_count += 1
#
#     print(f"Cache built. Successfully parsed {parsed_count} / {len(xml_files)} archetypes.")
#
#
# def parse_ontology(root):
#     """
#     Parses the <ontology> section into a simple dictionary.
#     Returns: {'at0001': {'text': 'Name', 'description': '...'}, ...}
#     """
#     ontology = {}
#     try:
#         # Find all <term_definitions> for 'en'
#         term_defs = root.findall(".//openEHR:term_definitions[@language='en']/openEHR:items", namespaces=NS)
#         for item in term_defs:
#             code = item.get('code')
#             if not code:
#                 continue
#
#             text_node = item.find("openEHR:items[@id='text']", namespaces=NS)
#             desc_node = item.find("openEHR:items[@id='description']", namespaces=NS)
#
#             ontology[code] = {
#                 'text': text_node.text if text_node is not None else "Unknown",
#                 'description': desc_node.text if desc_node.text is not None else ""
#             }
#         return ontology
#     except Exception as e:
#         print(f"Error parsing ontology: {e}")
#         return {}
#
#
# def parse_node(node, ontology):
#     """
#     (Robust v4)
#     Recursively parses a node in the <definition> tree.
#     This version correctly handles structural nodes like HISTORY, EVENT, and ITEM_TREE.
#     """
#     if node is None:
#         return None
#
#     node_id_node = node.find('openEHR:node_id', namespaces=NS)
#     rm_type_node = node.find('openEHR:rm_type_name', namespaces=NS)
#
#     if rm_type_node is None:
#         # This is a wrapper node without a type (like the children of <definition>).
#         # Just find its children and parse them.
#         fields = []
#         # Find DIRECT children attributes
#         child_nodes = node.findall("./openEHR:attributes/openEHR:children", namespaces=NS)
#         for child_node in child_nodes:
#             child_field = parse_node(child_node, ontology)
#             if child_field:
#                 fields.append(child_field)
#
#         # Hoist the fields: if this wrapper only had one child, just return that child.
#         if len(fields) == 1:
#             return fields[0]
#         elif len(fields) > 1:
#             return {'type': 'CONTAINER', 'fields': fields}
#         return None
#
#     rm_type = rm_type_node.text
#     node_id = node_id_node.text if node_id_node is not None else None
#
#     # --- 1. Handle DATA TYPE or STRUCTURAL nodes (no node_id) ---
#     if node_id is None:
#         # Data types
#         if rm_type == 'DV_TEXT':
#             return {'type': 'DV_TEXT'}
#         elif rm_type == 'DV_BOOLEAN':
#             return {'type': 'DV_BOOLEAN'}
#         elif rm_type == 'DV_DATE' or rm_type == 'DV_DATE_TIME':
#             return {'type': 'DV_DATE_TIME'}
#         elif rm_type == 'DV_QUANTITY':
#             return {'type': 'DV_QUANTITY'}
#         elif rm_type == 'DV_CODED_TEXT':
#             field_data = {'type': 'DV_CODED_TEXT', 'options': []}
#             code_nodes = node.findall('.//openEHR:code_list/openEHR:list', namespaces=NS)
#             for code_node in code_nodes:
#                 code_val_node = code_node.find('openEHR:value', namespaces=NS)
#                 if code_val_node is not None:
#                     code_val = code_val_node.text
#                     code_ontology = ontology.get(code_val, {'text': code_val})
#                     field_data['options'].append({
#                         'value': code_val,
#                         'label': code_ontology.get('text')
#                     })
#             return field_data
#
#         # Structural types: just recurse and return their children
#         elif rm_type in ['HISTORY', 'EVENT', 'POINT_EVENT', 'INTERVAL_EVENT']:
#             fields = []
#             child_nodes = node.findall("./openEHR:attributes/openEHR:children", namespaces=NS)
#             for child_node in child_nodes:
#                 child_field = parse_node(child_node, ontology)
#                 if child_field:
#                     fields.append(child_field)
#
#             if len(fields) == 1:
#                 return fields[0]
#             elif len(fields) > 1:
#                 return {'type': 'CONTAINER', 'fields': fields}
#
#         return None  # Unhandled node with no ID
#
#     # --- 2. Handle proper FIELD nodes (HAVE node_id) ---
#     ontology_data = ontology.get(node_id, {'text': f"({node_id})", 'description': ''})
#
#     occurrences = node.find('openEHR:occurrences', namespaces=NS)
#     is_required = False
#     is_multiple = False
#     if occurrences is not None:
#         lower = occurrences.find('openEHR:lower', namespaces=NS)
#         upper = occurrences.find('openEHR:upper', namespaces=NS)
#         upper_unbounded = occurrences.find('openEHR:upper_unbounded', namespaces=NS)
#         if lower is not None and lower.text is not None and int(lower.text) > 0:
#             is_required = True
#         if (upper is not None and upper.text is not None and int(upper.text) > 1) or \
#                 (upper_unbounded is not None and upper_unbounded.text == 'true'):
#             is_multiple = True
#
#     field_data = {
#         'id': node_id,
#         'label': ontology_data.get('text'),
#         'description': ontology_data.get('description'),
#         'type': rm_type,
#         'required': is_required,
#         'multiple': is_multiple,
#     }
#
#     if rm_type == 'ELEMENT':
#         value_node = node.find("./openEHR:attributes[@rm_attribute_name='value']/openEHR:children", namespaces=NS)
#         if value_node is not None:
#             value_field = parse_node(value_node, ontology)
#             if value_field:
#                 field_data.update({
#                     'type': value_field.get('type'),
#                     'options': value_field.get('options')
#                 })
#         return field_data
#
#     elif rm_type == 'CLUSTER':
#         field_data['fields'] = []
#         item_nodes = node.findall("./openEHR:attributes[@rm_attribute_name='items']/openEHR:children", namespaces=NS)
#         for item_node in item_nodes:
#             child_field = parse_node(item_node, ontology)
#             if child_field:
#                 field_data['fields'].append(child_field)
#         return field_data
#
#     elif rm_type == 'ARCHETYPE_SLOT':
#         field_data['type'] = 'SLOT'
#         return field_data
#
#     else:  # Any other container (COMPOSITION, OBSERVATION, SECTION, ITEM_TREE, etc.)
#
#         # Remap ITEM_TREE to look like a CLUSTER so the frontend renders it
#         if rm_type == 'ITEM_TREE':
#             field_data['type'] = 'CLUSTER'
#
#         field_data['fields'] = []
#         child_nodes = node.findall("./openEHR:attributes/openEHR:children", namespaces=NS)
#         for child_node in child_nodes:
#             child_field = parse_node(child_node, ontology)
#             if child_field:
#                 # If the child is a pseudo-container, hoist its fields up
#                 if child_field.get('type') == 'CONTAINER':
#                     field_data['fields'].extend(child_field.get('fields', []))
#                 else:
#                     field_data['fields'].append(child_field)
#         return field_data
#
#
# # --- API Endpoints ---
#
# @app.route('/')
# def serve_frontend():
#     """
#     API Endpoint: Serves the index.html file as the main page.
#     """
#     return app.send_static_file('../test/index.html')
#
#
# @app.route('/api/archetypes', methods=['GET'])
# def get_archetype_list():
#     """
#     API Endpoint: Returns the cached list of all archetypes.
#     """
#     list_data = [v for v in ARCHETYPE_CACHE.values() if v.get('name')]
#     list_data.sort(key=lambda x: x['name'])
#     return jsonify(list_data)
#
#
# @app.route('/api/archetype/<path:archetype_id>', methods=['GET'])
# def get_archetype_definition(archetype_id):
#     """
#     API Endpoint: Parses a single archetype and returns its
#     form definition as JSON.
#     """
#
#     # Automatically strip the .xml suffix if it was added to the URL
#     if archetype_id.endswith('.xml'):
#         archetype_id = archetype_id[:-4]
#
#     # 1. Find the archetype in the cache
#     cached_data = ARCHETYPE_CACHE.get(archetype_id)
#
#     if not cached_data:
#         print(f"Cache miss. Could not find ID: {archetype_id}")
#         abort(404, description=f"Archetype '{archetype_id}' not found in cache.")
#
#     try:
#         # 2. Parse the full XML file
#         tree = etree.parse(cached_data['path'])
#         root = tree.getroot()
#
#         # 3. Parse the ontology into a simple dict
#         ontology_dict = parse_ontology(root)
#
#         # 4. Find the main <definition> node
#         definition_node = root.find('.//openEHR:definition', namespaces=NS)
#         if definition_node is None:
#             abort(404, description="No <definition> found in XML.")
#
#         # 5. Start the recursive parse!
#         form_definition = parse_node(definition_node, ontology_dict)
#
#         # 6. Return the JSON
#         if form_definition:
#             return jsonify(form_definition)
#         else:
#             abort(500, description="Failed to parse form definition.")
#
#     except Exception as e:
#         print(f"Error parsing {archetype_id}: {e}")
#         abort(500, description=f"Failed to parse archetype: {e}")
#
#
# @app.route('/api/ehr/save', methods=['POST'])
# def save_ehr_document():
#     """
#     API Endpoint: Receives form data and saves it to the ehr_documents table.
#     """
#     if not request.json:
#         abort(400, description="Missing JSON data.")
#
#     form_data = request.json
#
#     # 1. Extract required metadata from the form data
#     # NOTE: You MUST ensure the frontend passes patient_id and archetype_id.
#
#     # We'll use the archetype ID from the route path (if applicable) or get a fixed one from data
#     # Since the frontend only sends the form data object, we assume archetypeId is a fixed value
#     # or you've included it in the form data (e.g., form_data['archetype_id'])
#
#     archetype_id = form_data.get('archetypeId')  # Assumes frontend adds this key
#     patient_id = form_data.get('patientId', 'PAT-UNKNOWN')  # Assumes frontend adds this key
#
#     # Fallback/Error check
#     if not archetype_id:
#         abort(400, description="Missing 'archetypeId' in form data.")
#
#     # 2. Connect to DB
#     conn = get_db_connection()
#     if conn is None:
#         abort(500, description="Database connection failed.")
#
#     try:
#         cur = conn.cursor()
#
#         # We save the entire received JSON object directly into the JSONB column
#         insert_query = """
#                        INSERT INTO ehr_documents (archetype_id, patient_id, data)
#                        VALUES (%s, %s, %s) RETURNING id; \
#                        """
#
#         # Convert Python dict to a JSON string for PostgreSQL
#         json_data_str = json.dumps(form_data)
#
#         cur.execute(insert_query, (archetype_id, patient_id, json_data_str))
#
#         saved_id = cur.fetchone()[0]
#         conn.commit()
#         cur.close()
#         conn.close()
#
#         return jsonify({
#             'status': 'success',
#             'message': 'Document saved successfully',
#             'record_id': saved_id,
#             'archetype_id': archetype_id
#         }), 201
#
#     except Exception as e:
#         conn.rollback()
#         print(f"Database insertion error: {e}")
#         abort(500, description=f"Failed to save document to database: {e}")
#     finally:
#         if conn:
#             conn.close()
#
# # --- Run the App ---
# if __name__ == '__main__':
#     # Build the cache on startup *before* running the app
#     build_archetype_cache()
#     print("Starting backend server on http://127.0.0.1:5000")
#     app.run(debug=True, port=5000)