/**
 * dashboard.js — Renders the timetable and charts on the dashboard page.
 */

const MEAL_TYPES = ['breakfast', 'lunch', 'snacks', 'dinner'];
const MEAL_EMOJIS = { breakfast: '🌅', lunch: '☀️', snacks: '🍎', dinner: '🌙' };
const DAY_NAMES = ['Mon', 'Tue', 'Wed', 'Thu', 'Fri', 'Sat', 'Sun'];
const TARGET_CALORIES = 2000;

let currentWeekStart = null;
let caloriesChart = null;
let healthChart = null;

// ── Date Helpers ─────────────────────────────────────────────────────────────

function getMondayOf(dateStr) {
  const d = new Date(dateStr + 'T00:00:00');
  const day = d.getDay(); // 0=Sun
  const diff = (day === 0 ? -6 : 1 - day);
  d.setDate(d.getDate() + diff);
  return formatDate(d);
}

function formatDate(d) {
  return d.toISOString().slice(0, 10);
}

function addDays(dateStr, n) {
  const d = new Date(dateStr + 'T00:00:00');
  d.setDate(d.getDate() + n);
  return formatDate(d);
}

function todayStr() {
  return formatDate(new Date());
}

function isCurrentWeek(weekStart) {
  return getMondayOf(todayStr()) === weekStart;
}

function formatWeekLabel(weekStart) {
  const start = new Date(weekStart + 'T00:00:00');
  const end = new Date(weekStart + 'T00:00:00');
  end.setDate(end.getDate() + 6);
  const opts = { month: 'short', day: 'numeric' };
  return `${start.toLocaleDateString('en-IN', opts)} – ${end.toLocaleDateString('en-IN', opts)}`;
}

// ── Init ─────────────────────────────────────────────────────────────────────

document.addEventListener('DOMContentLoaded', async () => {
  const token = localStorage.getItem('ep_token');
  if (!token) { window.location.href = '/'; return; }

  const name = localStorage.getItem('ep_user_name') || 'User';
  document.getElementById('user-name').textContent = name;

  currentWeekStart = getMondayOf(todayStr());
  await loadWeek(currentWeekStart);
  await loadCharts();
});

// ── Week Navigation ───────────────────────────────────────────────────────────

async function changeWeek(direction) {
  currentWeekStart = addDays(currentWeekStart, direction * 7);
  document.getElementById('next-week').disabled = isCurrentWeek(currentWeekStart);
  await loadWeek(currentWeekStart);
}

// ── Load Week Data ────────────────────────────────────────────────────────────

async function loadWeek(weekStart) {
  document.getElementById('week-label').textContent = formatWeekLabel(weekStart);
  document.getElementById('next-week').disabled = isCurrentWeek(weekStart);

  const timetableEl = document.getElementById('timetable');
  timetableEl.innerHTML = '<div class="loading" style="grid-column:1/-1">Loading...</div>';

  try {
    const data = await getLogs(weekStart);
    if (!data) return;
    renderTimetable(data.timetable, weekStart);
    updateSummaryCards(data.timetable);
  } catch (e) {
    timetableEl.innerHTML = `<div class="loading" style="grid-column:1/-1;color:#ef4444">Error loading data</div>`;
    console.error(e);
  }
}

// ── Timetable Renderer ────────────────────────────────────────────────────────

function renderTimetable(timetable, weekStart) {
  const el = document.getElementById('timetable');
  el.innerHTML = '';

  const today = todayStr();
  const days = Array.from({ length: 7 }, (_, i) => addDays(weekStart, i));

  // Header row: blank + 7 day headers
  el.appendChild(makeEl('div', 'tt-header-blank'));
  days.forEach((day, i) => {
    const header = makeEl('div', `tt-day-header${day === today ? ' today' : ''}`);
    const dayName = DAY_NAMES[i];
    const dayNum = day.slice(8); // DD
    header.innerHTML = `<strong>${dayName}</strong><br/>${dayNum}`;
    el.appendChild(header);
  });

  // 4 meal rows
  MEAL_TYPES.forEach(meal => {
    // Meal label cell
    const label = makeEl('div', 'tt-meal-label');
    label.textContent = `${MEAL_EMOJIS[meal]} ${meal.charAt(0).toUpperCase() + meal.slice(1)}`;
    el.appendChild(label);

    // 7 day cells
    days.forEach(day => {
      const cell = makeEl('div', `tt-cell${day === today ? ' today-col' : ''}`);
      const items = timetable[day]?.[meal] || [];

      if (items.length === 0) {
        const empty = makeEl('span', 'tt-empty');
        empty.textContent = '—';
        cell.appendChild(empty);
      } else {
        items.forEach(item => {
          cell.appendChild(renderFoodItem(item));
        });
      }
      el.appendChild(cell);
    });
  });
}

function renderFoodItem(item) {
  const div = makeEl('div', `food-item ${item.is_healthy ? 'healthy' : 'unhealthy'}`);

  const name = makeEl('div', 'food-name');
  name.textContent = item.food_name;
  name.title = item.food_name; // full name on hover

  const cal = makeEl('div', 'food-cal');
  cal.textContent = `${item.calories} kcal`;

  const badge = makeEl('span', `food-badge ${item.is_healthy ? 'badge-healthy' : 'badge-unhealthy'}`);
  badge.textContent = item.is_healthy ? 'Healthy' : 'Unhealthy';

  div.appendChild(name);
  div.appendChild(cal);
  div.appendChild(badge);
  return div;
}

// ── Summary Cards ─────────────────────────────────────────────────────────────

function updateSummaryCards(timetable) {
  const today = todayStr();
  const todayLogs = Object.values(timetable[today] || {}).flat();
  const todayTotal = todayLogs.reduce((s, i) => s + i.calories, 0);

  const allLogs = Object.values(timetable).flatMap(day => Object.values(day).flat());
  const weekTotal = allLogs.reduce((s, i) => s + i.calories, 0);

  const healthyCount = allLogs.filter(i => i.is_healthy).length;
  const score = allLogs.length > 0 ? (1 + (healthyCount / allLogs.length) * 9).toFixed(1) : '—';

  document.getElementById('today-calories').textContent = todayTotal || '—';
  document.getElementById('week-calories').textContent = weekTotal || '—';
  document.getElementById('health-score').textContent = score;
}

// ── Charts ────────────────────────────────────────────────────────────────────

async function loadCharts() {
  try {
    const data = await getWeeklyCalories();
    if (!data) return;
    renderCaloriesChart(data.daily_calories);
    renderHealthChart(data.health_score_history);
  } catch (e) {
    console.error('Chart load error:', e);
  }
}

function renderCaloriesChart(dailyCalories) {
  const ctx = document.getElementById('caloriesChart').getContext('2d');
  const labels = Object.keys(dailyCalories).map(d => {
    const dt = new Date(d + 'T00:00:00');
    return dt.toLocaleDateString('en-IN', { weekday: 'short', day: 'numeric' });
  });
  const values = Object.values(dailyCalories);

  if (caloriesChart) caloriesChart.destroy();
  caloriesChart = new Chart(ctx, {
    type: 'bar',
    data: {
      labels,
      datasets: [
        {
          label: 'Calories',
          data: values,
          backgroundColor: values.map(v => v > TARGET_CALORIES ? '#fca5a5' : '#86efac'),
          borderRadius: 6,
        },
        {
          label: 'Target (2000)',
          data: new Array(values.length).fill(TARGET_CALORIES),
          type: 'line',
          borderColor: '#f97316',
          borderDash: [6, 3],
          borderWidth: 2,
          pointRadius: 0,
          fill: false,
        }
      ],
    },
    options: {
      responsive: true,
      plugins: { legend: { display: false } },
      scales: {
        y: { beginAtZero: true, ticks: { font: { size: 11 } } },
        x: { ticks: { font: { size: 11 } } },
      },
    },
  });
}

function renderHealthChart(healthHistory) {
  const ctx = document.getElementById('healthChart').getContext('2d');
  const sorted = [...healthHistory].reverse();
  const labels = sorted.map(r => {
    const d = new Date(r.week_start + 'T00:00:00');
    return d.toLocaleDateString('en-IN', { month: 'short', day: 'numeric' });
  });
  const scores = sorted.map(r => +(1 + (r.healthy_pct / 100) * 9).toFixed(1));

  if (healthChart) healthChart.destroy();
  healthChart = new Chart(ctx, {
    type: 'line',
    data: {
      labels,
      datasets: [{
        label: 'Health Score',
        data: scores,
        borderColor: '#22c55e',
        backgroundColor: 'rgba(34,197,94,0.1)',
        borderWidth: 2,
        pointBackgroundColor: '#22c55e',
        fill: true,
        tension: 0.3,
      }],
    },
    options: {
      responsive: true,
      plugins: { legend: { display: false } },
      scales: {
        y: { min: 1, max: 10, ticks: { font: { size: 11 } } },
        x: { ticks: { font: { size: 11 } } },
      },
    },
  });
}

// ── Utilities ─────────────────────────────────────────────────────────────────

function makeEl(tag, cls) {
  const el = document.createElement(tag);
  if (cls) el.className = cls;
  return el;
}
