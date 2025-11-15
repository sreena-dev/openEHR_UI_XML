from lxml import etree as ET
import os

NAMESPACES = {'openEHR': 'http://schemas.openehr.org/v1'}


def build_ontology_map(root):
    """
    Creates a dictionary mapping 'at' codes (e.g., 'at0001') to their
    human-readable text from the <ontology> section.
    """
    ontology_map = {}
    try:
        lang_node = root.find(
            f".//openEHR:ontology/openEHR:term_definitions[@language='en']", namespaces=NAMESPACES)

        if lang_node is None:
            lang_node = root.find('.//openEHR:ontology/openEHR:term_definitions', namespaces=NAMESPACES)

        if lang_node is None:
            print("Warning: Could not find <term_definitions> in ontology.")
            return {}

        for item in lang_node.findall('openEHR:items', namespaces=NAMESPACES):
            code = item.get('code')
            if not code:
                continue

            text_item = item.find('openEHR:items[@id="text"]', namespaces=NAMESPACES)
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
    node_id_node = child.find('openEHR:node_id', namespaces=NAMESPACES)
    if node_id_node is None:
        return None

    node_id = node_id_node.text
    rm_type = child.find('openEHR:rm_type_name', namespaces=NAMESPACES).text
    field_label = ontology_map.get(node_id, node_id)
    field = {'label': field_label, 'name': node_id}

    if rm_type == 'ELEMENT':
        # --- THIS IS THE FIX ---
        # Find <attributes> node that has a *child* <rm_attribute_name> with text 'value'
        value_node_parent = child.find('openEHR:attributes[openEHR:rm_attribute_name="value"]', namespaces=NAMESPACES)
        if value_node_parent:
            value_node = value_node_parent.find('openEHR:children', namespaces=NAMESPACES)
        else:
            value_node = None
        # -----------------------

        if value_node:
            value_rm_type = value_node.find('openEHR:rm_type_name', namespaces=NAMESPACES).text
            field['rm_type'] = value_rm_type

            if value_rm_type == 'DV_TEXT':
                field['type'] = 'text'
            elif value_rm_type == 'DV_QUANTITY':
                field['type'] = 'number'
                try:
                    units = value_node.find('.//openEHR:units', namespaces=NAMESPACES).text
                    field['units'] = units
                except AttributeError:
                    field['units'] = None
            elif value_rm_type == 'DV_DATE_TIME':
                field['type'] = 'datetime-local'
            elif value_rm_type == 'DV_DATE':
                field['type'] = 'date'
            elif value_rm_type == 'DV_COUNT':
                field['type'] = 'number'
                field['step'] = 1
            elif value_rm_type == 'DV_BOOLEAN':
                field['type'] = 'checkbox'
                field['default'] = False
            elif value_rm_type == 'DV_CODED_TEXT':
                field['type'] = 'select'
                field['options'] = []
                try:
                    code_list = value_node.findall('.//openEHR:code_list', namespaces=NAMESPACES)
                    for code_item in code_list:
                        code_val = code_item.text
                        option_label = ontology_map.get(code_val, code_val)
                        field['options'].append({'value': code_val, 'label': option_label})
                except Exception as e:
                    print(f"Warning: Could not parse options for {node_id}: {e}")
            else:
                field['type'] = value_rm_type
        else:
            print(f"Warning: No 'value' attribute found for ELEMENT {node_id}")
            field['type'] = 'unsupported_element'

    elif rm_type == 'ARCHETYPE_SLOT':
        field['type'] = 'slot'
        try:
            field['allows'] = child.find('.//openEHR:includes/openEHR:string_expression', namespaces=NAMESPACES).text
        except AttributeError:
            field['allows'] = 'any'

    elif rm_type == 'CLUSTER':
        field['type'] = 'cluster'
        field['children'] = []
        # --- THIS IS THE FIX ---
        item_attributes = child.find('openEHR:attributes[openEHR:rm_attribute_name="items"]', namespaces=NAMESPACES)
        # -----------------------
        if item_attributes:
            for sub_child in item_attributes.findall('openEHR:children', namespaces=NAMESPACES):
                sub_field = get_form_field(sub_child, ontology_map)
                if sub_field:
                    field['children'].append(sub_field)

    else:
        field['type'] = rm_type

    return field


def parse_archetype_to_form(xml_file):
    """
    Main function to parse an openEHR XML file and return a list
    of form field definitions.
    """
    try:
        if not os.path.exists(xml_file):
            print(f"Error: File not found at {xml_file}")
            return []

        tree = ET.parse(xml_file)
        root = tree.getroot()

        ontology_map = build_ontology_map(root)
        if not ontology_map:
            print(f"Warning: Ontology map is empty for {xml_file}. Labels may be missing.")

        form_fields = []
        definition = root.find('.//openEHR:definition', namespaces=NAMESPACES)
        if definition is None:
            return []

        definition_rm_type = definition.find('openEHR:rm_type_name', namespaces=NAMESPACES)
        if definition_rm_type is not None and definition_rm_type.text == 'CLUSTER':
            root_node_id = definition.find('openEHR:node_id', namespaces=NAMESPACES).text
            root_label = ontology_map.get(root_node_id, root_node_id)

            if root_label == 'Cluster':
                root_label = os.path.basename(xml_file)

            root_field = {
                'label': root_label,
                'name': root_node_id,
                'type': 'cluster',
                'children': []
            }

            # --- THIS IS THE FIX ---
            cluster_items = definition.find('openEHR:attributes[openEHR:rm_attribute_name="items"]',
                                            namespaces=NAMESPACES)
            # -----------------------

            if cluster_items:
                for child in cluster_items.findall('openEHR:children', namespaces=NAMESPACES):
                    field = get_form_field(child, ontology_map)
                    if field:
                        root_field['children'].append(field)

            if root_field['children']:
                form_fields.append(root_field)
            else:
                # This warning is what you were seeing, it's not a crash
                print(f"Warning: CLUSTER {root_node_id} had no parsable children.")

        else:
            definition_type = definition_rm_type.text if definition_rm_type is not None else "unknown"
            print(f"Warning: Archetype {xml_file} is not a CLUSTER, it's a {definition_type}. Parser may not work.")

        # --- THIS IS THE FIX ---
        # Don't fail if the list is empty, just return the empty list.
        # The backend.py will handle this.
        return form_fields
        # -----------------------

    except Exception as e:
        print(f"CRITICAL PARSER ERROR for {xml_file}: {e}")
        return []  # Return empty list on crash