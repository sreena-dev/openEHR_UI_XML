import React from 'react';

// This is a recursive component. It renders a field.
// If the field is a "cluster", it renders a <fieldset> and then
// calls *itself* to render the cluster's children.

function FormField({ field, value, onChange }) {
  const { type, label, name, options, units, children } = field;

  // Helper to handle all input changes
  const handleChange = (e) => {
    const { type, checked, value } = e.target;
    onChange(name, type === 'checkbox' ? checked : value);
  };

  switch (type) {
    case 'text':
    case 'number':
    case 'date':
    case 'datetime-local':
      return (
        <div className="form-group">
          <label htmlFor={name}>
            {label} {units && <span>({units})</span>}
          </label>
          <input
            type={type}
            id={name}
            name={name}
            value={value || ''}
            onChange={handleChange}
          />
        </div>
      );

    case 'checkbox':
      return (
        <div className="form-group-checkbox">
          <input
            type="checkbox"
            id={name}
            name={name}
            checked={!!value}
            onChange={handleChange}
          />
          <label htmlFor={name}>{label}</label>
        </div>
      );

    case 'select':
      return (
        <div className="form-group">
          <label htmlFor={name}>{label}</label>
          <select id={name} name={name} value={value || ''} onChange={handleChange}>
            <option value="">-- Select an option --</option>
            {options.map(opt => (
              <option key={opt.value} value={opt.value}>
                {opt.label}
              </option>
            ))}
          </select>
        </div>
      );

    case 'cluster':
      return (
        <fieldset className="cluster-group">
          <legend>{label}</legend>
          {/* --- RECURSION --- */}
          {children.map(childField => (
            <FormField
              key={childField.name}
              field={childField}
              value={value ? value[childField.name] : undefined}
              onChange={(childName, childValue) => {
                // When a child changes, update this cluster's object
                const newValue = { ...(value || {}), [childName]: childValue };
                onChange(name, newValue);
              }}
            />
          ))}
        </fieldset>
      );

    case 'slot':
      return (
        <div className="form-group">
          <label htmlFor={name}>{label} (SLOT)</label>
          <input type="text" id={name} name={name} placeholder={field.allows} disabled />
        </div>
      );

    default:
      return (
        <div className="form-group">
          <label>Unsupported field type: {type}</label>
        </div>
      );
  }
}

export default FormField;