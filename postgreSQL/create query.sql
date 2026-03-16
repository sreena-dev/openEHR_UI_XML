-- Table to store submitted openEHR form data (EHR Documents)
CREATE TABLE ehr_documents (
    id BIGSERIAL PRIMARY KEY,

    -- Fixed Metadata Columns (Relational for fast lookups)
    archetype_id TEXT NOT NULL,
    patient_id TEXT NOT NULL,  -- You will need to pass this from the frontend/context
    recorded_by TEXT,          -- Composer ID/Name
    
    -- Temporal Data
    recorded_at TIMESTAMP WITH TIME ZONE DEFAULT NOW() NOT NULL,

    -- The Data Body
    data JSONB NOT NULL
);

-- Index for fast searching *within* the JSONB data (Critical)
CREATE INDEX idx_ehr_documents_data_gin ON ehr_documents USING GIN (data);

-- Standard indexes for common relational lookups
CREATE INDEX idx_ehr_documents_patient_id ON ehr_documents (patient_id);
CREATE INDEX idx_ehr_documents_archetype_id ON ehr_documents (archetype_id);