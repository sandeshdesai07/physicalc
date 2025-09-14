// frontend/src/App.js
import React, { useState } from "react";

const API_BASE = process.env.REACT_APP_API_BASE_URL || "http://34.100.131.244:8000";

function App() {
  const [text, setText] = useState("");
  const [loading, setLoading] = useState(false);
  const [resp, setResp] = useState(null);
  const [error, setError] = useState(null);

  async function ask() {
    setLoading(true);
    setError(null);
    setResp(null);
    try {
      const r = await fetch(`${API_BASE}/api/ask`, {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ user_id: 1, text })
      });
      if (!r.ok) {
        const txt = await r.text();
        throw new Error(`HTTP ${r.status}: ${txt}`);
      }
      const j = await r.json();
      setResp(j);
    } catch (e) {
      setError(String(e));
    } finally {
      setLoading(false);
    }
  }

  return (
    <div style={{ padding: 24, fontFamily: "system-ui, Arial" }}>
      <h1>Physicalc — Ask physics/math</h1>

      <textarea
        rows={4}
        cols={60}
        value={text}
        onChange={(e) => setText(e.target.value)}
        placeholder="e.g. kinetic energy of 5kg at 10 m/s or m=5 v=10 kinetic energy"
        style={{ marginBottom: 12 }}
      />
      <br />
      <button onClick={ask} disabled={loading || !text.trim()}>
        {loading ? "Thinking…" : "Ask"}
      </button>

      {error && (
        <div style={{ marginTop: 12, color: "crimson" }}>
          <strong>Error:</strong> <pre style={{ whiteSpace: "pre-wrap" }}>{error}</pre>
        </div>
      )}

      {resp && (
        <div style={{ marginTop: 16 }}>
          <h3>Response</h3>
          <pre style={{ whiteSpace: "pre-wrap" }}>{JSON.stringify(resp, null, 2)}</pre>
        </div>
      )}
    </div>
  );
}

export default App;
