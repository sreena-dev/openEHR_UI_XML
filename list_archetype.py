import os
import glob
from lxml import etree
from flask import Flask, jsonify
from flask_cors import CORS

# --- Config ---
# Path to your XML files.
# This script assumes your 'openEHR_xml' folder is in the same directory.
ARCHETYPE_ROOT_DIR = 'openEHR_xml'

app = Flask(__name__)
CORS(app)  # This lets your frontend call the API.


def parse_archetype_header(xml_file):
    """
    Parses an ADL 1.4 XML file to get its ID and human-readable name.
    This is a "quick and dirty" parser for the list, not a full ADL parser.
    """
    try:
        tree = etree.parse(xml_file)
        root = tree.getroot()

        # Define the XML namespaces. The main one has no prefix.
        ns = {'openEHR': 'http://schemas.openehr.org/v1'}

        # 1. Get the Archetype ID
        # Uses lxml `find` with the namespace.
        archetype_id_node = root.find('.//openEHR:archetype_id/openEHR:value', namespaces=ns)
        if archetype_id_node is None or archetype_id_node.text is None:
            return None

        archetype_id = archetype_id_node.text

        # 2. Get the human-readable name from the ontology
        # We look for the <term_definitions> for 'en', then the item with code 'at0000'
        concept_code = root.find('.//openEHR:concept', namespaces=ns).text

        name_node = root.find(
            f".//openEHR:term_definitions[@language='en']/openEHR:items[@code='{concept_code}']/openEHR:items[@id='text']",
            namespaces=ns)

        if name_node is None or name_node.text is None:
            # Fallback if 'en' isn't found or 'text' isn't there
            name = archetype_id
        else:
            name = name_node.text

        return {
            'id': archetype_id,
            'name': name
        }

    except etree.XMLSyntaxError:
        print(f"Error parsing {xml_file}. Skipping.")
        return None
    except Exception as e:
        print(f"Generic error on {xml_file}: {e}. Skipping.")
        return None


@app.route('/api/archetypes', methods=['GET'])
def get_archetype_list():
    """
    API Endpoint: Scans all directories and returns a list of archetypes.
    """
    print("Scanning for archetypes...")

    # Use glob to recursively find all .xml files in the root dir
    # The '/**/' means "all subdirectories"
    xml_files = glob.glob(os.path.join(ARCHETYPE_ROOT_DIR, '**', '*.xml'), recursive=True)

    archetypes_list = []

    for f in xml_files:
        header_data = parse_archetype_header(f)
        if header_data:
            archetypes_list.append(header_data)

    print(f"Found and parsed {len(archetypes_list)} archetypes.")

    # Sort the list by name, alphabetically
    archetypes_list.sort(key=lambda x: x['name'])

    return jsonify(archetypes_list)


# --- Run the App ---
if __name__ == '__main__':
    print("Starting backend server on http://127.0.0.1:5000")
    # `debug=True` auto-reloads the server when you save the file.
    app.run(debug=True, port=9000)