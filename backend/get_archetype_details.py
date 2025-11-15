import xml.etree.ElementTree as ET
import os

# This namespace is critical. The XMLs use it.
NAMESPACES = {'openEHR': 'http://schemas.openehr.org/v1'}


def build_ontology_map(root):
    """
    Creates a dictionary mapping 'at' codes (e.g., 'at0001') to their
    human-readable text from the <ontology> section.
    """
    ontology_map = {}
    try:
        # Find the 'en' language term definitions
        # You could make 'en' a variable if you need to support other languages
        term_definitions = root.find(
            ".//openEHR:ontology/openEHR:term_definitions/[openEHR:language/openEHR:code_string='en']",
            NAMESPACES
        )

        # Fallback if 'en' isn't found
        if term_definitions is None:
            term_definitions = root.find('.//openEHR:ontology/openEHR:term_definitions', NAMESPACES)

        if term_definitions is None:
            print("Warning: Could not find <term_definitions> in ontology.")
            return {}

        # Iterate over all <items code="...">
        for item in term_definitions.findall('openEHR:items', NAMESPACES):
            code = item.get('code')
            if not code:
                continue

            # Find the <items id="text"> child for the label
            text_item = item.find('openEHR:items[@id="text"]', NAMESPACES)
            if text_item is not None and text_item.text:
                ontology_map[code] = text_item.text.strip()

    except Exception as e:
        print(f"Error building ontology map: {e}")

    return ontology_map


def get_form_field(child, ontology_map):
    """
    Parses a single <children> element from the <definition> and
    translates it into a form field dictionary.
    """
    node_id = child.find('openEHR:node_id', NAMESPACES).text
    rm_type = child.find('openEHR:rm_type_name', NAMESPACES).text

    # Get the human-readable label from our map
    field_label = ontology_map.get(node_id, node_id)  # Default to node_id if not found

    field = {'label': field_label, 'name': node_id}

    # Determine input type based on rm_type_name
    if rm_type == 'DV_TEXT':
        field['type'] = 'text'

    elif rm_type == 'DV_QUANTITY':
        field['type'] = 'number'
        try:
            # Try to find defined units
            units = child.find('.//openEHR:units', NAMESPACES).text
            field['units'] = units
        except AttributeError:
            field['units'] = None

    elif rm_type == 'DV_DATE_TIME':
        field['type'] = 'datetime-local'

    elif rm_type == 'DV_DATE':
        field['type'] = 'date'

    elif rm_type == 'DV_COUNT':
        field['type'] = 'number'
        field['step'] = '1'  # Integer only

    elif rm_type == 'DV_BOOLEAN':
        field['type'] = 'checkbox'

    elif rm_type == 'DV_CODED_TEXT':
        field['type'] = 'select'  # Dropdown
        field['options'] = []
        try:
            # Find all the <code_list> items
            code_list = child.findall('.//openEHR:code_list', NAMESPACES)
            for code_item in code_list:
                code_val = code_item.text
                # Look up the human-readable text for this option
                option_label = ontology_map.get(code_val, code_val)
                field['options'].append({'value': code_val, 'label': option_label})
        except Exception as e:
            print(f"Warning: Could not parse options for {node_id}: {e}")

    elif rm_type == 'ARCHETYPE_SLOT':
        # This is a placeholder for another *entire* archetype.
        # We'll just mark it as a 'slot' for now.
        field['type'] = 'slot'
        try:
            field['allows'] = child.find('.//openEHR:includes/openEHR:string_expression', NAMESPACES).text
        except AttributeError:
            field['allows'] = 'any'

    else:
        field['type'] = rm_type  # Default to the RM type if unhandled

    return field


def get_archetype_details(archetype_name):
    """
    Main function to parse an openEHR XML file and return a list
    of form field definitions.
    """
    # Assuming your 'cluster' folder is in the same directory as this script
    base_dir = os.path.dirname(os.path.abspath(__file__))
    folder_path = os.path.join(base_dir, 'cluster')

    # Sanitize input to prevent directory traversal
    safe_name = os.path.basename(archetype_name)
    xml_file_path = os.path.join(folder_path, safe_name)

    if not os.path.exists(xml_file_path):
        return {'error': f'File not found: {safe_name}'}

    try:
        tree = ET.parse(xml_file_path)
        root = tree.getroot()

        # 1. Build the dictionary of all human-readable names
        ontology_map = build_ontology_map(root)
        if not ontology_map:
            print(f"Could not build ontology for {safe_name}. Labels may be missing.")

        form_fields = []

        # 2. Find the main definition block
        definition = root.find('.//openEHR:definition', NAMESPACES)
        if definition is None:
            return {'error': f'No <definition> found in {safe_name}.'}

        # 3. Find all <children> under the 'items' attribute
        item_attributes = definition.find('openEHR:attributes[@rm_attribute_name="items"]', NAMESPACES)

        if item_attributes:
            children = item_attributes.findall('openEHR:children', NAMESPACES)
            for child in children:
                # 4. Process each child into a form field
                try:
                    # Skip nodes without a node_id (internal structures)
                    if child.find('openEHR:node_id', NAMESPACES) is not None:
                        field = get_form_field(child, ontology_map)
                        form_fields.append(field)
                except Exception as e:
                    print(f"Error parsing a child node: {e}")

        # Return the complete list of form fields
        return {'form_fields': form_fields}

    except ET.ParseError as e:
        return {'error': f"Error parsing XML file {safe_name}: {e}"}
    except Exception as e:
        return {'error': f"An unexpected error occurred: {e}"}