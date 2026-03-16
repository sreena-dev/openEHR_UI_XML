import React, { useState, useEffect, useRef } from 'react';
import { useParams, Link } from 'react-router-dom';
import { LocalizationProvider } from '@mui/x-date-pickers/LocalizationProvider';
import { AdapterDayjs } from '@mui/x-date-pickers/AdapterDayjs';
import { DateTimePicker } from '@mui/x-date-pickers/DateTimePicker';
import dayjs from 'dayjs';

const API_URL = 'http://127.0.0.1:9000';

function MbMaterialDatePicker({ path, label }) {
  const [val, setVal] = useState(null);
  const targetRef = useRef(null);

  useEffect(() => {
    const el = targetRef.current;
    if (el) {
       Object.defineProperty(el, 'data', {
         get() { return targetRef.current.__val ? targetRef.current.__val.toISOString() : null; },
         set(v) { 
           const newDay = v ? dayjs(v) : null;
           setVal(newDay); 
           targetRef.current.__val = newDay;
         },
         configurable: true
       });
    }
  }, []);

  const handleChange = (newVal) => {
    setVal(newVal);
    if (targetRef.current) {
        targetRef.current.__val = newVal;
        targetRef.current.dispatchEvent(new CustomEvent('mb-input', { bubbles: true, composed: true }));
    }
  };

  return (
    <div style={{ width: '100%', position: 'relative', zIndex: 10 }}>
      <LocalizationProvider dateAdapter={AdapterDayjs}>
        <DateTimePicker 
           label={label}
           value={val}
           onChange={handleChange}
           slotProps={{ textField: { fullWidth: true, size: 'small', style: { backgroundColor: 'white' } } }}
        />
      </LocalizationProvider>
      <div ref={targetRef} path={path} style={{ display: 'none' }} />
    </div>
  );
}

/**
 * FormPage: The heart of the clinical application.
 * Dynamically renders openEHR templates using Medblocks-UI web components.
 *
 * KEY FEATURES:
 * - Direct Web Template to Medblocks-UI mapping
 * - EHRbase v2 compatible path construction (with indices)
 * - Patient EHR linking lifecycle
 * - Structured audit logging of all submissions
 */
function FormPage() {
  const { templateId } = useParams();
  const decodedTemplateId = decodeURIComponent(templateId);

  const [webTemplate, setWebTemplate] = useState(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState(null);
  const [submitting, setSubmitting] = useState(false);
  const [submitResult, setSubmitResult] = useState(null);
  const [patientId, setPatientId] = useState('');
  const [ehrId, setEhrId] = useState(null);
  const [ehrCreating, setEhrCreating] = useState(false);

  const formRef = useRef(null);

  // Load the web template on mount
  useEffect(() => {
    setLoading(true);
    fetch(`${API_URL}/api/web-template/${encodeURIComponent(decodedTemplateId)}`)
      .then(res => {
        if (!res.ok) throw new Error(`Template '${decodedTemplateId}' not found`);
        return res.json();
      })
      .then(data => {
        setWebTemplate(data);
        setLoading(false);
      })
      .catch(err => {
        setError(err.message);
        setLoading(false);
      });
  }, [decodedTemplateId]);

  // Handle Patient EHR Link
  const handleCreateEhr = async () => {
    if (!patientId.trim()) {
      setError('Please enter a Patient ID');
      return;
    }
    setEhrCreating(true);
    setError(null);
    try {
      const res = await fetch(`${API_URL}/api/ehr`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ patient_id: patientId.trim() }),
      });
      const data = await res.json();
      if (!res.ok) throw new Error(data.description || 'Failed to create EHR');
      setEhrId(data.ehr_id);
    } catch (err) {
      setError(err.message);
    } finally {
      setEhrCreating(false);
    }
  };

  // Humanizes labels from node identifiers
  const getLabel = (node) => {
    const name = node.localizedName || node.name || node.id;
    if (!name) return '';
    return name.charAt(0).toUpperCase() + name.slice(1).replace(/_/g, ' ');
  };

  /**
   * Recursive renderer for Web Template nodes.
   * Maps nodes to specific Medblocks-UI components.
   */
  const renderTree = (node, parentPath = '') => {
    if (!node) return null;

    const id = node.id || '';
    const max = node.max;
    
    // EHRbase v2 indexing rule: 
    // Nodes that can repeat (max > 1 or max === -1) need a :0 index suffix
    const needsIndex = max === -1 || max > 1;
    const currentPath = parentPath 
      ? `${parentPath}/${id}${needsIndex ? ':0' : ''}`
      : id;

    const rmType = node.rmType || '';
    const label = getLabel(node);

    // ─── Group / Cluster Containers ──────────────────────────────
    const groups = [
      'SECTION', 'OBSERVATION', 'EVALUATION', 'INSTRUCTION', 'ACTION', 
      'ADMIN_ENTRY', 'CLUSTER', 'EVENT', 'POINT_EVENT', 'ITEM_TREE', 
      'ITEM_LIST', 'ITEM_TABLE', 'ITEM_SINGLE', 'ACTIVITY', 'HISTORY',
      'EVENT_CONTEXT'
    ];
    
    if (groups.includes(rmType)) {
      const children = node.children?.map(child => renderTree(child, currentPath)).filter(Boolean);
      if (!children || children.length === 0) return null;

      // Wrap meaningful clinical containers in a themed section/box
      const isTopLevel = ['OBSERVATION', 'EVALUATION', 'INSTRUCTION', 'ACTION', 'SECTION', 'ADMIN_ENTRY', 'EVENT_CONTEXT'].includes(rmType);
      
      return (
        <div key={currentPath} className={isTopLevel ? 'form-section' : 'form-cluster'}>
          {isTopLevel && <h3 className="section-title">{label}</h3>}
          {!isTopLevel && (rmType === 'CLUSTER' || rmType === 'EVENT') && <div className="cluster-label">{label}</div>}
          <div className="section-content">
            {children}
          </div>
        </div>
      );
    }

    // ─── Fallthrough for other structural nodes ─────────────────
    if (node.children && node.children.length > 0 && rmType !== 'ELEMENT') {
      return node.children.map(child => renderTree(child, currentPath)).filter(Boolean);
    }

    // ─── Individual Input Elements & Direct Data Types ───────────
    const isElement = rmType === 'ELEMENT';
    const isDataType = rmType.startsWith('DV_');

    if (isElement || isDataType) {
      const leaf = isElement 
        ? (node.children?.find(c => c.rmType.startsWith('DV_')) || node.children?.[0])
        : node;
      
      const dataType = leaf?.rmType || '';
      
      switch (dataType) {
        case 'DV_QUANTITY':
          return (
            <div key={currentPath} className="field-row">
              <mb-quantity path={currentPath} label={label}>
                {leaf.inputs?.find(i => i.suffix === 'unit')?.list?.map(u => (
                  <mb-unit key={u.value} unit={u.value} label={u.label || u.value} />
                ))}
              </mb-quantity>
            </div>
          );

        case 'DV_CODED_TEXT': {
          const options = leaf.inputs?.find(i => i.type === 'CODED_TEXT')?.list || [];
          return (
            <div key={currentPath} className="field-row">
              <mb-select path={currentPath} label={label}>
                {options.map(opt => (
                  <mb-option key={opt.value} value={opt.value} label={opt.label || opt.value} />
                ))}
              </mb-select>
            </div>
          );
        }

        case 'DV_TEXT':
          return (
            <div key={currentPath} className="field-row">
              <mb-input path={currentPath} label={label} />
            </div>
          );

        case 'DV_DATE_TIME':
          return (
            <div key={currentPath} className="field-row">
              <MbMaterialDatePicker path={currentPath} label={label} />
            </div>
          );

        case 'DV_COUNT':
          return (
            <div key={currentPath} className="field-row">
              <mb-count path={currentPath} label={label} />
            </div>
          );

        case 'DV_BOOLEAN':
          return (
            <div key={currentPath} className="field-row">
              <mb-checkbox path={currentPath} label={label} />
            </div>
          );

        default:
          return null;
      }
    }

    // Skip technical nodes (History, Item Tree etc) but look at their children
    if (node.children) {
      return node.children.map(child => renderTree(child, currentPath)).filter(Boolean);
    }

    return null;
  };

  // Submit Handler
  const handleSubmit = async (e) => {
    e.preventDefault();
    if (!ehrId) {
      setError('Wait! Please link a Patient ID first.');
      return;
    }

    const form = formRef.current;
    const rawData = form.data; // Medblocks mb-form provides all data as a flat JSON

    // Path cleanup for EHRbase v2 requirement
    // Ensure all paths start with the templateId prefix if missing
    const finalData = {};
    Object.entries(rawData).forEach(([path, value]) => {
        if (value === undefined || value === null || value === '') return;
        const fullPath = path.startsWith(decodedTemplateId) ? path : `${decodedTemplateId}/${path}`;
        finalData[fullPath] = value;
    });

    if (Object.keys(finalData).length === 0) {
      setError('Form is empty. Please enter some clinical data.');
      return;
    }

    setSubmitting(true);
    setError(null);
    setSubmitResult(null);

    try {
      const res = await fetch(`${API_URL}/api/composition`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({
          ehr_id: ehrId,
          template_id: decodedTemplateId,
          composition: finalData,
        }),
      });

      const data = await res.json();
      if (!res.ok) throw new Error(data.description || 'Submission failed');

      setSubmitResult(data);
    } catch (err) {
      setError(err.message);
    } finally {
      setSubmitting(false);
    }
  };

  if (loading) return (
    <div className="form-page loading">
      <div className="spinner"></div>
      <p>Consulting EHRbase records...</p>
    </div>
  );

  const tree = webTemplate?.tree || webTemplate?.webTemplate?.tree;

  return (
    <div className="form-page">
      <header className="form-page-header">
        <Link to="/" className="btn-back">← All Templates</Link>
        <div className="header-meta">
          <h2>{getLabel(tree)}</h2>
          <span className="badge-outline">{decodedTemplateId}</span>
        </div>
      </header>

      {/* EHR Context Card */}
      <section className="ehr-section">
        <h3>👤 Clinical Context</h3>
        <div className="ehr-controls">
          <input 
            type="text" 
            className="patient-input"
            placeholder="Search Patient ID (e.g. PAT-001)" 
            value={patientId}
            onChange={e => setPatientId(e.target.value)}
            disabled={!!ehrId}
          />
          {!ehrId ? (
            <button className="btn btn-secondary" onClick={handleCreateEhr} disabled={ehrCreating}>
              {ehrCreating ? 'Linking...' : 'Link Medical Record'}
            </button>
          ) : (
            <div className="ehr-linked">
              <span className="ehr-check">✓</span>
              <span>Linked to EHR: <b>{ehrId.split('-')[0]}...</b></span>
              <div className="ehr-actions">
                <Link to={`/history/${ehrId}`} className="btn btn-link">View History</Link>
                <button className="btn btn-link" onClick={() => setEhrId(null)}>Change</button>
              </div>
            </div>
          )}
        </div>
      </section>

      {error && (
        <div className="error-banner">
          <span>⚠️</span> {error}
          <button className="error-dismiss" onClick={() => setError(null)}>✕</button>
        </div>
      )}

      {/* Clinical Form */}
      <mb-form ref={formRef}>
        <div className="clinical-grid">
          {tree?.children?.map(child => renderTree(child))}
        </div>

        <div className="form-footer">
          <button 
            type="button" 
            className="btn btn-primary btn-lg" 
            onClick={handleSubmit}
            disabled={submitting || !ehrId}
          >
            {submitting ? 'Saving...' : '💾 Save Clinical Note'}
          </button>
          {!ehrId && <p className="hint">Please establish patient context before saving.</p>}
        </div>
      </mb-form>

      {/* Success Modal/View */}
      {submitResult && (
        <div className="success-overlay">
          <div className="success-card card">
            <div className="check-ring">
              <svg viewBox="0 0 52 52"><circle cx="26" cy="26" r="25" fill="none"/><path fill="none" d="M14.1 27.2l7.1 7.2 16.7-16.8"/></svg>
            </div>
            <h3>Composition Successfully Persisted</h3>
            <p>Clinical information has been saved to EHRbase with full audit trails.</p>
            <div className="success-meta">
              <div><span>UID:</span> <code>{submitResult.composition_uid}</code></div>
              <div><span>EHR:</span> <code>{submitResult.ehr_id}</code></div>
            </div>
            <button className="btn btn-primary" onClick={() => setSubmitResult(null)}>Close</button>
          </div>
        </div>
      )}
    </div>
  );
}

export default FormPage;