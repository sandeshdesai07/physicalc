// src/App.js
import React, { useState } from "react";
import { askQuestion } from "./api";   // <- use centralised API helper

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
      const j = await askQuestion(1, text);   // call helper (works in dev & prod)
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
