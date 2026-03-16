"""
openEHR Medical Application — Flask Backend

This backend acts as a secure proxy layer between the React/Medblocks-UI frontend
and the EHRbase Clinical Data Repository. It does NOT store clinical data locally.

SAFETY: All clinical data operations are audit-logged. Input validation is enforced
on every endpoint that handles patient data.
"""

import os
import re
import json
import logging
from datetime import datetime
from functools import wraps

from flask import Flask, jsonify, abort, request
from flask_cors import CORS
from werkzeug.exceptions import HTTPException
from dotenv import load_dotenv

from ehrbase_client import EHRbaseClient, EHRbaseError

# Load environment variables from .env file
load_dotenv()

# ─── Logging Setup ────────────────────────────────────────────────────
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s [%(levelname)s] %(name)s: %(message)s',
    datefmt='%Y-%m-%d %H:%M:%S'
)
logger = logging.getLogger('openehr_backend')

# ─── Flask App Setup ──────────────────────────────────────────────────
app = Flask(__name__)

# CORS: Restrict to allowed origins only
cors_origins = os.getenv('CORS_ORIGINS', 'http://localhost:3000').split(',')
CORS(app, origins=cors_origins)

# ─── EHRbase Client ───────────────────────────────────────────────────
ehrbase = EHRbaseClient()

# ─── Rate Limiting ────────────────────────────────────────────────────
try:
    from flask_limiter import Limiter
    from flask_limiter.util import get_remote_address
    limiter = Limiter(
        get_remote_address,
        app=app,
        default_limits=["200 per minute"],
        storage_uri="memory://",
    )
    logger.info("Rate limiting enabled")
except ImportError:
    limiter = None
    logger.warning("flask-limiter not installed. Rate limiting disabled.")


# ─── Error Handlers ───────────────────────────────────────────────────

@app.errorhandler(HTTPException)
def handle_http_exception(e):
    """Return JSON instead of HTML for HTTP errors."""
    response = e.get_response()
    response.data = json.dumps({
        "code": e.code,
        "name": e.name,
        "description": e.description,
    })
    response.content_type = "application/json"
    return response


@app.errorhandler(EHRbaseError)
def handle_ehrbase_error(e):
    """Handle EHRbase-specific errors."""
    status = e.status_code or 502
    return jsonify({
        "code": status,
        "name": "EHRbase Error",
        "description": str(e),
    }), status


# ─── Input Validation Helpers ─────────────────────────────────────────

def validate_patient_id(patient_id):
    """
    SAFETY: Validates patient ID format to prevent injection attacks.
    Patient IDs must be alphanumeric with hyphens/underscores, max 64 chars.
    """
    if not patient_id or not isinstance(patient_id, str):
        return False
    if len(patient_id) > 64:
        return False
    # Allow alphanumeric, hyphens, underscores, and dots
    if not re.match(r'^[a-zA-Z0-9._-]+$', patient_id):
        return False
    return True


def validate_template_id(template_id):
    """
    Validates template ID format.
    """
    if not template_id or not isinstance(template_id, str):
        return False
    if len(template_id) > 128:
        return False
    # Allow alphanumeric, hyphens, underscores, dots, and parentheses
    if not re.match(r'^[a-zA-Z0-9._()\- ]+$', template_id):
        return False
    return True


def sanitize_string(value, max_length=1000):
    """
    SAFETY: Sanitize string inputs by stripping control characters
    and limiting length.
    """
    if not isinstance(value, str):
        return value
    # Remove control characters except newlines and tabs
    cleaned = re.sub(r'[\x00-\x08\x0b\x0c\x0e-\x1f\x7f]', '', value)
    return cleaned[:max_length]


# ─── API ENDPOINTS ────────────────────────────────────────────────────

# ── Health Check ──

@app.route('/api/health', methods=['GET'])
def health_check():
    """
    Health check endpoint verifying backend, DB, and EHRbase connectivity.
    """
    from db import check_db_health
    
    ehrbase_status = ehrbase.health_check()
    db_status = 'healthy' if check_db_health() else 'unreachable'
    
    return jsonify({
        'backend': 'healthy',
        'database': db_status,
        'ehrbase': ehrbase_status,
        'timestamp': datetime.utcnow().isoformat() + 'Z'
    })


# ── Template Management ──

@app.route('/api/templates', methods=['GET'])
def get_templates():
    """
    API Endpoint: Returns the list of all available templates from EHRbase.

    Response: JSON array of template objects:
    [
        {
            "template_id": "blood_pressure",
            "concept": "blood_pressure",
            "archetype_id": "openEHR-EHR-...",
            "created_timestamp": "..."
        },
        ...
    ]
    """
    try:
        templates = ehrbase.list_templates()

        # Enrich with display-friendly names
        for t in templates:
            # Use concept as display name, fallback to template_id
            name = t.get('concept', t.get('template_id', 'Unknown'))
            # Convert underscores/dots to spaces and title-case for display
            t['display_name'] = name.replace('_', ' ').replace('.', ' ').title()

        logger.info(f"Serving {len(templates)} templates to frontend")
        return jsonify(templates)

    except EHRbaseError as e:
        logger.error(f"Failed to fetch templates: {e}")
        abort(502, description="Could not fetch templates from EHRbase.")


@app.route('/api/web-template/<path:template_id>', methods=['GET'])
def get_web_template(template_id):
    """
    API Endpoint: Returns the Web Template JSON for a specific template.
    This is consumed by the Medblocks-UI frontend to render forms.

    Args:
        template_id: The template identifier (e.g., 'blood_pressure')
    """
    if not validate_template_id(template_id):
        abort(400, description="Invalid template ID format.")

    try:
        web_template = ehrbase.get_web_template(template_id)
        return jsonify(web_template)

    except EHRbaseError as e:
        if e.status_code == 404:
            abort(404, description=f"Template '{template_id}' not found in EHRbase.")
        logger.error(f"Error fetching web template '{template_id}': {e}")
        abort(502, description="Could not fetch web template from EHRbase.")


# ── EHR Management ──

@app.route('/api/ehr', methods=['POST'])
def create_ehr():
    """
    API Endpoint: Creates a new EHR for a patient, or returns existing one.

    Request body: { "patient_id": "PAT-001" }
    Response: { "ehr_id": "uuid-...", "patient_id": "PAT-001" }

    SAFETY: Validates patient ID and prevents duplicate EHR creation.
    """
    if not request.json:
        abort(400, description="Missing JSON body.")

    patient_id = request.json.get('patient_id')
    if not validate_patient_id(patient_id):
        abort(400, description="Invalid patient_id. Must be alphanumeric, max 64 characters.")

    logger.info(f"AUDIT: EHR creation requested for patient_id={patient_id}")

    try:
        result = ehrbase.create_ehr(patient_id)
        ehr_id = result.get('ehr_id', {}).get('value', '')

        # It says 'created' if EHRbase generated one, or 'exists' if it returned early
        logger.info(f"AUDIT: EHR created/found for patient {patient_id}: ehr_id={ehr_id}")

        return jsonify({
            'ehr_id': ehr_id,
            'patient_id': patient_id,
            'status': 'success'
        }), 201

    except EHRbaseError as e:
        logger.error(f"AUDIT: Failed to create/fetch EHR for patient {patient_id}: {e}")
        abort(502, description=f"Failed to create/fetch EHR: {e}")


@app.route('/api/ehr/<string:patient_id>', methods=['GET'])
def get_ehr_for_patient(patient_id):
    """
    API Endpoint: Look up the EHR ID for a given patient.
    """
    if not validate_patient_id(patient_id):
        abort(400, description="Invalid patient_id format.")

    try:
        result = ehrbase.get_ehr_by_subject(patient_id)
        if result is None:
            abort(404, description=f"No EHR found for patient '{patient_id}'.")

        ehr_id = result.get('ehr_id', {}).get('value', '')
        return jsonify({
            'ehr_id': ehr_id,
            'patient_id': patient_id
        })

    except EHRbaseError as e:
        logger.error(f"Error looking up EHR for patient {patient_id}: {e}")
        abort(502, description="Could not query EHRbase.")


# ── Composition Management ──

@app.route('/api/composition', methods=['POST'])
def submit_composition():
    """
    API Endpoint: Receives Flat JSON from the frontend and submits it to EHRbase.

    SAFETY: This is the primary clinical data submission endpoint.
    All submissions are validated and audit-logged.

    Request body:
    {
        "ehr_id": "uuid-...",
        "template_id": "blood_pressure",
        "composition": { ... flat JSON key-value pairs ... }
    }
    """
    if not request.json:
        abort(400, description="Missing JSON body.")

    data = request.json
    ehr_id = data.get('ehr_id')
    template_id = data.get('template_id')
    composition = data.get('composition', {})

    # Validate required fields
    if not ehr_id:
        abort(400, description="Missing 'ehr_id'.")
    if not validate_template_id(template_id):
        abort(400, description="Invalid or missing 'template_id'.")
    if not composition or not isinstance(composition, dict):
        abort(400, description="Missing or invalid 'composition' data.")

    # Sanitize string values in the composition
    sanitized_composition = {}
    for key, value in composition.items():
        sanitized_key = sanitize_string(key, max_length=500)
        if isinstance(value, str):
            sanitized_composition[sanitized_key] = sanitize_string(value)
        else:
            sanitized_composition[sanitized_key] = value

    logger.info(
        f"AUDIT: Composition submission - ehr_id={ehr_id}, "
        f"template_id={template_id}, field_count={len(sanitized_composition)}"
    )

    try:
        result = ehrbase.submit_composition(ehr_id, template_id, sanitized_composition)

        comp_uid = result.get('compositionUid', 'unknown')
        logger.info(
            f"AUDIT: Composition saved successfully - "
            f"ehr_id={ehr_id}, template_id={template_id}, uid={comp_uid}"
        )

        return jsonify({
            'status': 'success',
            'message': 'Composition saved to EHRbase successfully',
            'composition_uid': comp_uid,
            'ehr_id': ehr_id,
            'template_id': template_id,
            'timestamp': datetime.utcnow().isoformat() + 'Z'
        }), 201

    except EHRbaseError as e:
        logger.error(
            f"AUDIT: Composition submission FAILED - "
            f"ehr_id={ehr_id}, template_id={template_id}, error={e}"
        )
        abort(
            e.status_code or 502,
            description=f"Failed to save composition to EHRbase: {e}"
        )


# ── AQL Query ──

@app.route('/api/query', methods=['POST'])
def run_aql_query():
    """
    API Endpoint: Execute an AQL query against EHRbase.

    Request body: { "aql": "SELECT ... FROM EHR ..." }
    Response: { "columns": [...], "rows": [...] }
    """
    if not request.json or 'aql' not in request.json:
        abort(400, description="Missing 'aql' query in request body.")

    aql = request.json.get('aql', '')

    # SAFETY: Basic AQL injection prevention
    # AQL should not contain dangerous keywords for data modification
    dangerous_patterns = ['DELETE', 'UPDATE', 'DROP', 'INSERT', 'ALTER', 'TRUNCATE']
    aql_upper = aql.upper()
    for pattern in dangerous_patterns:
        if pattern in aql_upper:
            logger.warning(f"AUDIT: Blocked potentially dangerous AQL query containing '{pattern}'")
            abort(400, description=f"AQL queries containing '{pattern}' are not allowed.")

    try:
        result = ehrbase.query_aql(aql, request.json.get('query_parameters'))
        return jsonify(result)
    except EHRbaseError as e:
        if e.status_code == 400:
            abort(400, description=f"Invalid AQL query: {e}")
        logger.error(f"AQL query error: {e}")
        abort(502, description="Failed to execute query against EHRbase.")


# ─── Run the App ──────────────────────────────────────────────────────

if __name__ == '__main__':
    from db import initialize_database
    
    port = int(os.getenv('FLASK_PORT', 9000))
    debug = os.getenv('FLASK_DEBUG', 'true').lower() == 'true'

    logger.info(f"Starting openEHR backend on http://127.0.0.1:{port}")
    logger.info(f"EHRbase URL: {ehrbase.base_url}")

    # Initialize PostgreSQL mapping table
    db_initialized = initialize_database()
    if not db_initialized:
        logger.warning("Could not initialize PostgreSQL database. Ensure the container is running or .env is correct.")

    # Verify EHRbase connectivity on startup
    health = ehrbase.health_check()
    if health['status'] == 'healthy':
        logger.info(f"EHRbase is healthy. {health.get('template_count', 0)} templates available.")
    else:
        logger.warning(f"EHRbase connectivity issue: {health.get('error', 'unknown')}")

    app.run(debug=debug, port=port)