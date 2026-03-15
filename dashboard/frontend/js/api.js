/**
 * api.js — Authenticated fetch wrapper for the EatPulse API.
 */

function getToken() {
  return localStorage.getItem('ep_token');
}

function logout() {
  localStorage.removeItem('ep_token');
  localStorage.removeItem('ep_user_name');
  window.location.href = '/';
}

async function apiFetch(path, options = {}) {
  const token = getToken();
  if (!token) {
    window.location.href = '/';
    return null;
  }

  const headers = {
    'Content-Type': 'application/json',
    'Authorization': `Bearer ${token}`,
    ...(options.headers || {}),
  };

  const resp = await fetch(path, { ...options, headers });

  if (resp.status === 401) {
    logout();
    return null;
  }

  if (!resp.ok) {
    const text = await resp.text();
    throw new Error(`API error ${resp.status}: ${text}`);
  }

  return resp.json();
}

async function getMe() {
  return apiFetch('/api/me');
}

async function getLogs(weekStart) {
  const qs = weekStart ? `?week_start=${weekStart}` : '';
  return apiFetch(`/api/logs${qs}`);
}

async function getWeeklyCalories() {
  return apiFetch('/api/calories/weekly');
}
