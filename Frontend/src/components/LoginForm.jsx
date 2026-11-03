import { useState } from "react";

export default function LoginForm({ fields, submitLabel, busyLabel, onSubmit }) {
  const [values, setValues] = useState(() => {
    const initial = {};
    fields.forEach(field => {
      initial[field.name] = "";
    });
    return initial;
  });
  const [error, setError] = useState("");
  const [busy, setBusy] = useState(false);
  
  function handleChange(name, value) {
    setValues(prev => ({
      ...prev,
      [name]: value,
    }));
  }
  
  async function handleSubmit(e) {
    e.preventDefault();
    setError("");
    setBusy(true);
    
    try {
      await onSubmit(values);
    } catch (err) {
      setError(err.message);
    } finally {
      setBusy(false);
    }
  }
  
  return (
    <form onSubmit={handleSubmit} className="space-y-6">
      {error && (
        <div className="bg-accent border-l-2 border-secondary p-3 font-mono text-xs text-black">
          <p>{error}</p>
        </div>
      )}
      
      {fields.map(field => (
        <div key={field.name}>
          <label
            htmlFor={field.name}
            className="block font-mono text-xs uppercase tracking-wider font-medium text-black mb-2"
          >
            {field.label}
          </label>
          <input
            id={field.name}
            type={field.type}
            autoComplete={field.autoComplete}
            placeholder={field.placeholder}
            value={values[field.name] ?? ""}
            onChange={(e) => handleChange(field.name, e.target.value)}
            disabled={busy}
            className="w-full bg-white text-black font-body text-sm border-2 border-black rounded-none px-3 py-3 placeholder:text-secondary focus:outline-none focus:ring-2 focus:ring-secondary focus:ring-offset-2 disabled:cursor-not-allowed"
          />
        </div>
      ))}
      
      <button
        type="submit"
        disabled={busy}
        className="w-full bg-secondary hover:bg-black text-white font-body font-semibold text-sm rounded-none py-3.5 px-4 transition-colors disabled:bg-secondary disabled:cursor-not-allowed"
      >
        {busy ? busyLabel : submitLabel}
      </button>
    </form>
  );
}
