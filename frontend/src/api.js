// src/api.js
// centralised API helper — avoids embedding absolute backend IP in production builds

const DEFAULT_LOCAL = 'http://localhost:8000';

// If developer set REACT_APP_API_BASE_URL, use it.
// Otherwise: use localhost in development, and empty string (relative path) in production.
const BASE =
  process.env.REACT_APP_API_BASE_URL ??
  (process.env.NODE_ENV === 'development' ? DEFAULT_LOCAL : '');

// Helper to build URL: if BASE is empty this returns a relative path "/api/..."
function apiPath(path) {
  if (!BASE) {
    // relative path — good for production behind Vercel rewrites (HTTPS frontend -> Vercel -> HTTP backend)
    return `/api${path.startsWith('/') ? path : `/${path}`}`;
  }
  // absolute or explicit base provided
  return `${BASE}${path.startsWith('/') ? path : `/${path}`}`;
}

export async function askQuestion(userId, text) {
  const url = apiPath('/ask');
  const res = await fetch(url, {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({ user_id: userId, text })
  });

  if (!res.ok) {
    const txt = await res.text().catch(() => '');
    throw new Error(`API error ${res.status}: ${txt}`);
  }
  return res.json();
}
