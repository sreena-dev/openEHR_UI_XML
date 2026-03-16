import React, { useState, useEffect } from 'react';
import { useParams, Link } from 'react-router-dom';

const API_URL = 'http://127.0.0.1:9000';

/**
 * HistoryView: Allows clinicians to search and retrieve clinical events for a patient.
 * Powered by EHRbase AQL (Archetype Query Language).
 */
function HistoryView() {
  const { ehrId } = useParams();
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState(null);
  const [history, setHistory] = useState([]);
  const [aqlQuery, setAqlQuery] = useState('');

  const fetchHistory = async () => {
    setLoading(true);
    setError(null);
    try {
      // Powerful AQL query to find all compositions for this EHR
      const aql = `
        SELECT
            c/uid/value as uid,
            c/name/value as template_id,
            c/context/start_time/value as start_time,
            c/composer/name as composer
        FROM EHR e [ehr_id/value='${ehrId}']
        CONTAINS COMPOSITION c
        ORDER BY c/context/start_time/value DESC
      `;
      
      const res = await fetch(`${API_URL}/api/query`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ aql }),
      });
      
      const data = await res.json();
      if (!res.ok) throw new Error(data.description || 'Failed to fetch clinical history');
      
      setHistory(data.rows || []);
    } catch (err) {
      setError(err.message);
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    if (ehrId) fetchHistory();
  }, [ehrId]);

  return (
    <div className="history-page">
      <header className="page-header">
        <Link to="/" className="btn-back">← Dashboard</Link>
        <div className="header-meta">
          <h2>Clinical History</h2>
          <span className="badge-outline">EHR: {ehrId.substring(0, 8)}...</span>
        </div>
      </header>

      {error && (
        <div className="error-banner">
          <span>⚠️</span> {error}
          <button className="error-dismiss" onClick={() => setError(null)}>✕</button>
        </div>
      )}

      <section className="history-list card">
        <div className="list-header">
          <h3>Recent Clinical Events</h3>
          <button className="btn btn-secondary btn-sm" onClick={fetchHistory} disabled={loading}>
            {loading ? 'Refreshing...' : '🔄 Refresh'}
          </button>
        </div>

        {loading ? (
          <div className="loading-state">
            <div className="spinner"></div>
            <p>Scanning EHRbase records...</p>
          </div>
        ) : history.length === 0 ? (
          <div className="empty-state">
            <p>No clinical events found for this patient record.</p>
          </div>
        ) : (
          <table className="history-table">
            <thead>
              <tr>
                <th>Template</th>
                <th>Recorded At</th>
                <th>Author</th>
                <th>Composition UID</th>
              </tr>
            </thead>
            <tbody>
              {history.map((row, idx) => (
                <tr key={idx}>
                  <td><span className="template-name">{row[1]}</span></td>
                  <td>{new Date(row[2]).toLocaleString()}</td>
                  <td>{row[3] || 'System User'}</td>
                  <td><code className="uid-compact">{row[0].split('::')[0]}...</code></td>
                </tr>
              ))}
            </tbody>
          </table>
        )}
      </section>
    </div>
  );
}

export default HistoryView;
