import React, { useState, useEffect } from 'react';
import { Link } from 'react-router-dom';

const API_URL = 'http://127.0.0.1:9000';

function SearchPage() {
  const [archetypes, setArchetypes] = useState([]); // Good: default is []
  const [searchTerm, setSearchTerm] = useState('');
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState(null);

  useEffect(() => {
    fetch(`${API_URL}/api/archetypes`)
      .then(res => {
        if (!res.ok) {
          throw new Error('Network response was not ok');
        }
        return res.json();
      })
      .then(data => {
        // --- THIS IS THE FIX ---
        // If data is null or undefined, use an empty array [] instead.
        setArchetypes(data || []);
        // -----------------------
        setLoading(false);
      })
      .catch(err => {
        console.error('Failed to fetch archetypes:', err);
        setError('Failed to load archetypes. Is the backend running?');
        setArchetypes([]); // Also set to empty array on error
        setLoading(false);
      });
  }, []);

  // Filter the list based on the search term
  // This line is now safe because 'archetypes' will always be an array.
  const filteredArchetypes = archetypes.filter(arch =>
    arch.name.toLowerCase().includes(searchTerm.toLowerCase())
  );

  return (
    <div>
      <h1>Search Archetypes</h1>
      <input
        type="text"
        className="search-input"
        placeholder="Start typing (e.g., 'address', 'symptom')..."
        value={searchTerm}
        onChange={e => setSearchTerm(e.target.value)}
      />
      <div className="results-list">
        {loading && <div className="result-item">Loading...</div>}
        {error && <div className="result-item error">{error}</div>}

        {/* This part is now safe */}
        {!loading && !error && filteredArchetypes.length === 0 && (
          <div className="result-item">No archetypes found.</div>
        )}

        {filteredArchetypes.map(arch => (
          <Link
            key={arch.id}
            to={`/form/${arch.id}`}
            className="result-item"
          >
            {arch.name}
            <span>{arch.id}</span>
          </Link>
        ))}
      </div>
    </div>
  );
}

export default SearchPage;