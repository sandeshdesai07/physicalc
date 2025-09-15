// src/api.js
const BASE = process.env.REACT_APP_API_BASE_URL || 'http://localhost:8000';

export async function askQuestion(userId, text) {
  const res = await fetch(`${BASE}/api/ask`, {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({ user_id: userId, text })
  });
  if (!res.ok) throw new Error(`API error ${res.status}`);
  return res.json();
}
