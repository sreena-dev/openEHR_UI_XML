import React, { useState, useEffect } from 'react';
import { Link } from 'react-router-dom';

const API_URL = 'http://127.0.0.1:9000';

function SearchPage() {
  const [templates, setTemplates] = useState([]);
  const [searchTerm, setSearchTerm] = useState('');
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState(null);
  const [ehrbaseStatus, setEhrbaseStatus] = useState(null);

  useEffect(() => {
    // Fetch health status
    fetch(`${API_URL}/api/health`)
      .then(res => res.json())
      .then(data => setEhrbaseStatus(data))
      .catch(() => setEhrbaseStatus({ backend: 'unreachable' }));

    // Fetch templates from EHRbase via backend proxy
    fetch(`${API_URL}/api/templates`)
      .then(res => {
        if (!res.ok) throw new Error('Failed to fetch templates from EHRbase');
        return res.json();
      })
      .then(data => {
        setTemplates(data || []);
        setLoading(false);
      })
      .catch(err => {
        console.error('Failed to fetch templates:', err);
        setError('Failed to load templates. Is EHRbase running?');
        setTemplates([]);
        setLoading(false);
      });
  }, []);

  const filteredTemplates = templates.filter(t => {
    const name = (t.display_name || t.template_id || '').toLowerCase();
    const id = (t.template_id || '').toLowerCase();
    const archetype = (t.archetype_id || '').toLowerCase();
    const term = searchTerm.toLowerCase();
    return name.includes(term) || id.includes(term) || archetype.includes(term);
  });

  return (
    <div className="search-page">
      {/* Status Banner */}
      <div className={`status-banner ${ehrbaseStatus?.ehrbase?.status === 'healthy' ? 'healthy' : 'warning'}`}>
        <span className="status-dot"></span>
        {ehrbaseStatus?.ehrbase?.status === 'healthy'
          ? `EHRbase Connected — ${ehrbaseStatus.ehrbase.template_count} templates available`
          : 'Checking EHRbase connection...'
        }
      </div>

      <div className="search-hero">
        <h2>Clinical Templates</h2>
        <p className="search-subtitle">
          Search and select an openEHR template to generate a standardized clinical form
        </p>
      </div>

      <div className="search-box-wrapper">
        <span className="search-icon">🔍</span>
        <input
          type="text"
          className="search-input"
          placeholder="Search templates (e.g., 'blood pressure', 'advance care')..."
          value={searchTerm}
          onChange={e => setSearchTerm(e.target.value)}
          id="template-search"
        />
        {searchTerm && (
          <button className="search-clear" onClick={() => setSearchTerm('')}>✕</button>
        )}
      </div>

      <div className="results-list">
        {loading && (
          <div className="result-item loading-item">
            <div className="loading-spinner"></div>
            <span>Loading templates from EHRbase...</span>
          </div>
        )}

        {error && (
          <div className="result-item error-item">
            <span className="error-icon">⚠️</span>
            {error}
          </div>
        )}

        {!loading && !error && filteredTemplates.length === 0 && (
          <div className="result-item empty-item">
            {searchTerm
              ? `No templates found matching "${searchTerm}"`
              : 'No templates found in EHRbase. Upload operational templates first.'
            }
          </div>
        )}

        {filteredTemplates.map(t => (
          <Link
            key={t.template_id}
            to={`/form/${encodeURIComponent(t.template_id)}`}
            className="result-item template-card"
            id={`template-${t.template_id}`}
          >
            <div className="template-info">
              <span className="template-name">{t.display_name || t.template_id}</span>
              <span className="template-id">{t.template_id}</span>
            </div>
            <div className="template-meta">
              <span className="template-archetype">{t.archetype_id}</span>
              <span className="template-arrow">→</span>
            </div>
          </Link>
        ))}
      </div>

      {!loading && !error && (
        <div className="results-count">
          Showing {filteredTemplates.length} of {templates.length} templates
        </div>
      )}
    </div>
  );
}

export default SearchPage;