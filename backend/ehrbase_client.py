"""
EHRbase REST API Client

Encapsulates all communication with the EHRbase Clinical Data Repository (CDR).
Handles authentication, template management, EHR creation, and composition submission.

SAFETY NOTE: This module handles clinical data — all errors are logged with context
for audit trail purposes. No clinical data is silently discarded.
"""

import os
import json
import logging
import requests
from datetime import datetime

logger = logging.getLogger(__name__)


class EHRbaseError(Exception):
    """Custom exception for EHRbase API errors."""
    def __init__(self, message, status_code=None, response_body=None):
        super().__init__(message)
        self.status_code = status_code
        self.response_body = response_body


class EHRbaseClient:
    """
    Client for EHRbase openEHR REST API.

    Supports:
    - Template listing and web template retrieval
    - EHR creation and lookup
    - Composition submission (Flat JSON format)
    - AQL querying
    """

    def __init__(self, base_url=None, username=None, password=None):
        self.base_url = (base_url or os.getenv('EHRBASE_BASE_URL', 'http://localhost:8080/ehrbase')).rstrip('/')
        self.username = username or os.getenv('EHRBASE_USER', 'admin')
        self.password = password or os.getenv('EHRBASE_PASSWORD', 'password')
        self.session = requests.Session()
        self.session.auth = (self.username, self.password)
        self.session.headers.update({
            'Accept': 'application/json',
        })
        logger.info(f"EHRbase client initialized for {self.base_url}")

    def _request(self, method, path, **kwargs):
        """
        Internal helper for making authenticated requests to EHRbase.
        Raises EHRbaseError on failure with full context for auditing.
        """
        url = f"{self.base_url}{path}"
        try:
            response = self.session.request(method, url, timeout=30, **kwargs)
            if response.status_code >= 400:
                error_body = response.text
                logger.error(
                    f"EHRbase API error: {method} {path} -> {response.status_code}: {error_body}"
                )
                raise EHRbaseError(
                    f"EHRbase returned {response.status_code}: {error_body}",
                    status_code=response.status_code,
                    response_body=error_body
                )
            return response
        except requests.exceptions.ConnectionError:
            logger.critical(f"Cannot connect to EHRbase at {self.base_url}")
            raise EHRbaseError(
                "Cannot connect to EHRbase. Is the Docker container running?",
                status_code=503
            )
        except requests.exceptions.Timeout:
            logger.error(f"EHRbase request timed out: {method} {path}")
            raise EHRbaseError("EHRbase request timed out.", status_code=504)

    # ─── Template Management ──────────────────────────────────────────

    def list_templates(self):
        """
        List all uploaded operational templates from EHRbase.

        Returns:
            list[dict]: Each dict has 'template_id', 'concept', 'archetype_id', 'created_timestamp'
        """
        response = self._request('GET', '/rest/openehr/v1/definition/template/adl1.4')
        templates = response.json()
        logger.info(f"Retrieved {len(templates)} templates from EHRbase")
        return templates

    def get_web_template(self, template_id):
        """
        Fetch the Web Template (simplified data template) for a given template ID.
        This is used by Medblocks-UI to render forms.

        Args:
            template_id: The template identifier (e.g., 'blood_pressure')

        Returns:
            dict: The Web Template JSON
        """
        response = self._request(
            'GET',
            f'/rest/ecis/v1/template/{template_id}',
            headers={'Accept': 'application/json'}
        )
        web_template = response.json()
        logger.info(f"Retrieved web template for '{template_id}'")
        return web_template

    def upload_template(self, opt_xml_content):
        """
        Upload an Operational Template (OPT) to EHRbase.

        Args:
            opt_xml_content: The XML content of the .opt file as string

        Returns:
            dict: Response from EHRbase confirming the upload
        """
        response = self._request(
            'POST',
            '/rest/openehr/v1/definition/template/adl1.4',
            data=opt_xml_content,
            headers={'Content-Type': 'application/xml'}
        )
        logger.info("Successfully uploaded operational template to EHRbase")
        # EHRbase returns 201 or 200 on success. May return empty body.
        if response.text:
            return response.json()
        return {'status': 'uploaded'}

    # ─── EHR Management ───────────────────────────────────────────────

    def create_ehr(self, subject_id, subject_namespace='default'):
        """
        Create a new EHR for a patient/subject in EHRbase and save mapping to PostgreSQL.

        SAFETY: Every patient MUST have exactly one EHR. This method checks
        the PostgreSQL mapping if an EHR already exists before creating a new one.
        """
        # First check persistent Postgres mapping for existing EHR
        from db import get_ehr_id_for_patient, save_patient_ehr_link
        
        existing_ehr_id = get_ehr_id_for_patient(subject_id)
        if existing_ehr_id:
            logger.info(f"EHR already exists in Postgres for subject {subject_id}: {existing_ehr_id}")
            return {'ehr_id': {'value': str(existing_ehr_id)}}

        # Create a new blank EHR
        response = self._request(
            'POST',
            '/rest/openehr/v1/ehr',
            headers={
                'Content-Type': 'application/json',
                'Prefer': 'return=representation'
            }
        )

        result = response.json()
        ehr_id = result.get('ehr_id', {}).get('value', 'unknown')

        # Store the patient-to-EHR mapping persistently in PostgreSQL
        if ehr_id != 'unknown':
            success = save_patient_ehr_link(subject_id, ehr_id)
            if not success:
                logger.error(f"Failed to persist EHR link for {subject_id} to {ehr_id}")

        logger.info(f"Created new EHR for subject {subject_id}: {ehr_id}")
        return result

    def get_ehr_by_subject(self, subject_id, subject_namespace='default'):
        """
        Look up an existing EHR by subject (patient) ID via Postgres mapping.
        """
        from db import get_ehr_id_for_patient
        
        # Check Postgres mapping first
        ehr_id = get_ehr_id_for_patient(subject_id)
        if ehr_id:
            try:
                return self.get_ehr(str(ehr_id))
            except EHRbaseError as e:
                logger.error(f"EHR mapping exists in DB but EHR not found in CDR for {subject_id}: {e}")
                return None
        return None

    def get_ehr(self, ehr_id):
        """
        Get an EHR by its ID.

        Args:
            ehr_id: The EHR UUID

        Returns:
            dict: The EHR object
        """
        response = self._request('GET', f'/rest/openehr/v1/ehr/{ehr_id}')
        return response.json()

    # ─── Composition Management ───────────────────────────────────────

    @staticmethod
    def _clean_flat_json(flat_json):
        """
        Clean flat JSON before submission to EHRbase.

        Removes:
        - Keys with empty/null/None values
        - Orphaned coded text sub-paths (|code, |terminology without |value)
        - Partial entries that would cause EHRbase to reject the composition

        SAFETY: This prevents invalid data from reaching EHRbase while
        preserving all valid clinical data.
        """
        cleaned = {}
        # First pass: collect all keys with non-empty values
        for key, value in flat_json.items():
            # Keep context keys (ctx/) always
            if key.startswith('ctx/'):
                cleaned[key] = value
                continue

            # Skip empty values
            if value is None or value == '' or value == []:
                continue

            cleaned[key] = value

        # Second pass: remove orphaned coded text sub-paths
        # If we have |code or |terminology but no corresponding |value, remove them
        keys_to_remove = set()
        coded_suffixes = ['|code', '|terminology', '|value', '|defining_code']

        for key in list(cleaned.keys()):
            if key.startswith('ctx/'):
                continue

            # Check if this is a sub-path of a coded text
            for suffix in coded_suffixes:
                if key.endswith(suffix):
                    base_path = key[:key.rfind(suffix)]
                    # Check if the base value path has actual data
                    value_key = base_path + '|value'
                    if value_key not in cleaned or not cleaned.get(value_key):
                        # Mark all related sub-paths for removal
                        for s in coded_suffixes:
                            keys_to_remove.add(base_path + s)
                    break

        for key in keys_to_remove:
            cleaned.pop(key, None)

        return cleaned

    def submit_composition(self, ehr_id, template_id, flat_json):
        """
        Submit a clinical composition to EHRbase in Flat JSON format.

        SAFETY: This is the primary method for persisting clinical data.
        All submissions are logged with timestamps for audit trail.

        Args:
            ehr_id: The EHR UUID for the patient
            template_id: The template ID this composition conforms to
            flat_json: The Flat JSON composition data (dict)

        Returns:
            dict: Contains composition UID and version info
        """
        # Add mandatory context fields if not present
        if 'ctx/language' not in flat_json:
            flat_json['ctx/language'] = 'en'
        if 'ctx/territory' not in flat_json:
            flat_json['ctx/territory'] = 'IN'
        if 'ctx/composer_name' not in flat_json:
            flat_json['ctx/composer_name'] = 'Clinical System'
        if 'ctx/time' not in flat_json:
            flat_json['ctx/time'] = datetime.utcnow().isoformat() + 'Z'

        # Clean the flat JSON: remove empty values and orphaned coded text sub-paths
        flat_json = self._clean_flat_json(flat_json)

        logger.info(
            f"AUDIT: Submitting composition for EHR={ehr_id}, template={template_id}, "
            f"time={flat_json.get('ctx/time')}, composer={flat_json.get('ctx/composer_name')}, "
            f"field_count={len(flat_json)}"
        )

        response = self._request(
            'POST',
            f'/rest/ecis/v1/composition',
            params={
                'ehrId': ehr_id,
                'templateId': template_id,
                'format': 'FLAT'
            },
            json=flat_json,
            headers={
                'Content-Type': 'application/json',
                'Prefer': 'return=representation'
            }
        )

        result = response.json()
        comp_uid = result.get('compositionUid', 'unknown')
        logger.info(f"AUDIT: Composition saved successfully. UID={comp_uid}")
        return result

    def get_composition(self, ehr_id, composition_uid, fmt='FLAT'):
        """
        Retrieve a composition by UID.

        Args:
            ehr_id: The EHR UUID
            composition_uid: The composition UID
            fmt: Format - 'FLAT', 'RAW', 'STRUCTURED'

        Returns:
            dict: The composition data
        """
        response = self._request(
            'GET',
            f'/rest/ecis/v1/composition/{composition_uid}',
            params={'ehrId': ehr_id, 'format': fmt}
        )
        return response.json()

    # ─── AQL Query ────────────────────────────────────────────────────

    def query_aql(self, aql_query, query_params=None):
        """
        Execute an AQL (Archetype Query Language) query against EHRbase.

        Args:
            aql_query: The AQL query string
            query_params: Optional dict of named query parameters

        Returns:
            dict: Query results with 'rows' and 'columns'
        """
        body = {"q": aql_query}
        if query_params:
            body["query_parameters"] = query_params

        logger.info(f"Executing AQL query: {aql_query[:100]}...")

        response = self._request(
            'POST',
            '/rest/openehr/v1/query/aql',
            json=body
        )
        result = response.json()
        row_count = len(result.get('rows', []))
        logger.info(f"AQL query returned {row_count} rows")
        return result

    # ─── Health Check ─────────────────────────────────────────────────

    def health_check(self):
        """
        Check if EHRbase is reachable and responding.

        Returns:
            dict: Status information
        """
        try:
            response = self._request('GET', '/rest/openehr/v1/definition/template/adl1.4')
            return {
                'status': 'healthy',
                'ehrbase_url': self.base_url,
                'template_count': len(response.json()),
                'timestamp': datetime.utcnow().isoformat() + 'Z'
            }
        except EHRbaseError as e:
            return {
                'status': 'unhealthy',
                'ehrbase_url': self.base_url,
                'error': str(e),
                'timestamp': datetime.utcnow().isoformat() + 'Z'
            }
