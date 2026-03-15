/**
 * auth.js — Handles Telegram Login Widget callback and JWT storage.
 */

// Called by the Telegram Login Widget on successful login
async function onTelegramAuth(user) {
  try {
    const resp = await fetch('/api/auth/telegram', {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify(user),
    });

    if (!resp.ok) {
      const err = await resp.json();
      alert('Login failed: ' + (err.detail || 'Unknown error'));
      return;
    }

    const data = await resp.json();
    localStorage.setItem('ep_token', data.access_token);
    localStorage.setItem('ep_user_name', user.first_name || 'User');

    // Redirect to dashboard
    window.location.href = '/dashboard.html';
  } catch (e) {
    console.error('Auth error:', e);
    alert('Login failed. Please try again.');
  }
}

// On page load: if already logged in, redirect to dashboard
document.addEventListener('DOMContentLoaded', () => {
  if (localStorage.getItem('ep_token')) {
    window.location.href = '/dashboard.html';
  }
});
