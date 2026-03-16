import os
from lxml import etree

xml_file = os.path.join('..', 'openEHR_xml', 'openEHR-EHR-CLUSTER.blood_cell_count.v0.xml')
ns = {'openEHR': 'http://schemas.openehr.org/v1'}

try:
    tree = etree.parse(xml_file)
    root = tree.getroot()
    archetype_id_node = root.find('.//openEHR:archetype_id/openEHR:value', namespaces=ns)
    if archetype_id_node is not None:
        raw_id = archetype_id_node.text
        print(f"Raw ID: '{raw_id}'")
        print(f"ID Has whitespace: {raw_id != raw_id.strip()}")
    
    concept_node = root.find('.//openEHR:concept', namespaces=ns)
    if concept_node is not None:
        raw_concept = concept_node.text
        print(f"Raw Concept: '{raw_concept}'")
        print(f"Concept Has whitespace: {raw_concept != raw_concept.strip()}")
    else:
        print("ID node not found")
except Exception as e:
    print(f"Error: {e}")
