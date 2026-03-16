"""
Database Connection and Initialization Module (PostgreSQL)

Handles connection pooling and robust interactions with the local PostgreSQL database
used for mapping Patient IDs to their corresponding EHRbase UUIDs.

SAFETY: We use parameterized queries exclusively to prevent SQL injection.
Connections are managed via context managers to prevent leaks.
"""

import os
import logging
from contextlib import contextmanager
import psycopg2
from psycopg2 import pool
from psycopg2.extras import RealDictCursor
from dotenv import load_dotenv

load_dotenv()
logger = logging.getLogger(__name__)

# Initialize connection pool
try:
    db_pool = psycopg2.pool.SimpleConnectionPool(
        1, 10,
        host=os.getenv('LOCAL_DB_HOST', 'localhost'),
        port=os.getenv('LOCAL_DB_PORT', '5433'),
        database=os.getenv('LOCAL_DB_NAME', 'OpenEHR_db'),
        user=os.getenv('LOCAL_DB_USER', 'postgres'),
        password=os.getenv('LOCAL_DB_PASSWORD', 'sreena7')
    )
    if db_pool:
        logger.info("PostgreSQL connection pool created successfully")
except Exception as e:
    logger.error(f"Failed to create PostgreSQL connection pool: {e}")
    db_pool = None

@contextmanager
def get_db_connection():
    """Context manager for safely acquiring and releasing database connections."""
    if not db_pool:
        raise Exception("Database connection pool is not initialized")
    
    conn = db_pool.getconn()
    try:
        yield conn
        # Commit by default if no exception was raised
        conn.commit()
    except Exception as e:
        conn.rollback()
        raise e
    finally:
        db_pool.putconn(conn)

def initialize_database():
    """
    Creates necessary tables on startup if they don't exist.
    """
    if not db_pool:
        logger.warning("Skipping DB initialization due to missing connection pool")
        return False
        
    try:
        with get_db_connection() as conn:
            with conn.cursor() as cur:
                # Table for patient_id -> ehr_id mapping
                cur.execute("""
                    CREATE TABLE IF NOT EXISTS patient_mapping (
                        patient_id VARCHAR(255) PRIMARY KEY,
                        ehr_id UUID NOT NULL,
                        created_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP
                    );
                """)
                logger.info("Database table 'patient_mapping' initialized successfully")
        return True
    except Exception as e:
        logger.error(f"Failed to initialize database tables: {e}")
        return False

def get_ehr_id_for_patient(patient_id):
    """
    Fetch the ehr_id for a given patient_id from the database.
    Returns None if not found.
    """
    try:
        with get_db_connection() as conn:
            with conn.cursor(cursor_factory=RealDictCursor) as cur:
                cur.execute(
                    "SELECT ehr_id FROM patient_mapping WHERE patient_id = %s",
                    (patient_id,)
                )
                result = cur.fetchone()
                return result['ehr_id'] if result else None
    except Exception as e:
        logger.error(f"Error querying patient map for {patient_id}: {e}")
        return None

def save_patient_ehr_link(patient_id, ehr_id):
    """
    Save the patient_id -> ehr_id link into the database using UPSERT.
    """
    try:
        with get_db_connection() as conn:
            with conn.cursor() as cur:
                cur.execute("""
                    INSERT INTO patient_mapping (patient_id, ehr_id)
                    VALUES (%s, %s)
                    ON CONFLICT (patient_id) DO UPDATE
                    SET ehr_id = EXCLUDED.ehr_id;
                """, (patient_id, ehr_id))
        return True
    except Exception as e:
        logger.error(f"Error saving patient map for {patient_id} ({ehr_id}): {e}")
        return False

def check_db_health():
    """
    Simple health check query.
    """
    try:
        with get_db_connection() as conn:
            with conn.cursor() as cur:
                cur.execute("SELECT 1;")
                cur.fetchone()
        return True
    except Exception:
        return False
