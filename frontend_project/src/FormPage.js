import React, { useState, useEffect } from 'react';
import { useParams, Link } from 'react-router-dom';
import FormField from './FormField'; // Our recursive component

const API_URL = 'http://127.0.0.1:9000';

function FormPage() {
  const { archetypeId } = useParams(); // Gets 'archetypeId' from the URL
  const [fields, setFields] = useState([]);
  const [formData, setFormData] = useState({});
  const [submittedJson, setSubmittedJson] = useState(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState(null);

  useEffect(() => {
    // Fetch the form structure for this *specific* archetype
    setLoading(true);
    setSubmittedJson(null);
    fetch(`${API_URL}/api/archetype/form/${archetypeId}`)
      .then(res => {
        if (!res.ok) { throw new Error(`Could not find archetype: ${archetypeId}`); }
        return res.json();
      })
      .then(data => {
        setFields(data);
        // Initialize the form data with default values
        const initialData = {};
        data.forEach(field => {
          if (field.type === 'checkbox') {
            initialData[field.name] = false;
          }
        });
        setFormData(initialData);
        setLoading(false);
      })
      .catch(err => {
        console.error('Failed to fetch form:', err);
        setError(err.message);
        setLoading(false);
      });
  }, [archetypeId]); // Re-run this if the archetypeId in the URL changes

  // This function is called by FormField components when they change
  const handleChange = (name, value) => {
    setFormData(prevData => ({
      ...prevData,
      [name]: value,
    }));
  };

  const handleSubmit = (e) => {
    e.preventDefault(); // Stop the page from reloading
    console.log("Final Form Data:", formData);
    setSubmittedJson(JSON.stringify(formData, null, 2));
  };

  if (loading) return <div>Loading form...</div>;
  if (error) return <div className="error">Error: {error}</div>;

  return (
    <div>
      <Link to="/">&larr; Back to Search</Link>
      <h1 className="form-title">Form: {archetypeId}</h1>
      <form onSubmit={handleSubmit}>
        {fields.map(field => (
          <FormField
            key={field.name}
            field={field}
            value={formData[field.name]}
            onChange={handleChange}
          />
        ))}
        <button type="submit" className="submit-btn">
          Submit and View JSON
        </button>
      </form>

      {/* This is your "View JSON" part */}
      {submittedJson && (
        <div className="json-output">
          <h2>Submitted JSON</h2>
          <pre>{submittedJson}</pre>
        </div>
      )}
    </div>
  );
}

export default FormPage;