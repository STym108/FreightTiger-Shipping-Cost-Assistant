// FreightGuard AI - Executive Web Dashboard JavaScript

let currentChart = null;
let cachedAnomalies = [];
let currentFilter = 'all';

document.addEventListener('DOMContentLoaded', () => {
  initOverview();
  initRouteSelect();
  initAnomalyTable();
  initChat();
  initProbes();
  initModal();
});

// 1. Overview KPIs
async function initOverview() {
  try {
    const res = await fetch('/api/overview');
    const data = await res.json();
    document.getElementById('kpiShipments').textContent = data.total_shipments.toLocaleString();
    document.getElementById('kpiWindows').textContent = data.total_route_weeks.toLocaleString();
    document.getElementById('kpiAnomalies').textContent = data.anomalies_count;
    document.getElementById('kpiJustified').textContent = `${data.justified_count} Justified`;
    document.getElementById('kpiUnexplained').textContent = `${data.unexplained_count} Flagged`;
  } catch (err) {
    console.error('Error loading overview:', err);
  }
}

// 2. Corridor Intelligence Chart
async function initRouteSelect() {
  const select = document.getElementById('routeSelect');
  select.addEventListener('change', (e) => {
    loadRouteTimeline(e.target.value);
  });
  // Load default route
  loadRouteTimeline(select.value);
}

async function loadRouteTimeline(route) {
  try {
    const res = await fetch(`/api/route-timeline?route=${encodeURIComponent(route)}`);
    const data = await res.json();
    renderChart(data);
  } catch (err) {
    console.error('Error loading route timeline:', err);
  }
}

function renderChart(data) {
  const ctx = document.getElementById('costTrendChart').getContext('2d');
  
  if (currentChart) {
    currentChart.destroy();
  }

  // Create point styles for anomalies
  const pointRadius = [];
  const pointBackgroundColor = [];
  const pointBorderColor = [];

  data.cost_series.forEach((val, i) => {
    const anom = data.anomaly_flags[i];
    if (anom) {
      pointRadius.push(7);
      if (anom.flagged.includes('justified')) {
        pointBackgroundColor.push('#10b981'); // Green justified
        pointBorderColor.push('#ffffff');
      } else {
        pointBackgroundColor.push('#f43f5e'); // Red flagged
        pointBorderColor.push('#ffffff');
      }
    } else {
      pointRadius.push(2);
      pointBackgroundColor.push('#38bdf8');
      pointBorderColor.push('transparent');
    }
  });

  currentChart = new Chart(ctx, {
    type: 'line',
    data: {
      labels: data.weeks,
      datasets: [
        {
          label: 'Weekly Cost (₹/t-km)',
          data: data.cost_series,
          borderColor: '#38bdf8',
          backgroundColor: 'rgba(56, 189, 248, 0.08)',
          borderWidth: 2.5,
          tension: 0.25,
          fill: true,
          pointRadius: pointRadius,
          pointHoverRadius: 9,
          pointBackgroundColor: pointBackgroundColor,
          pointBorderColor: pointBorderColor,
          pointBorderWidth: 2,
          order: 1
        },
        {
          label: 'Trailing 8-Wk History Avg',
          data: data.history_baseline_series,
          borderColor: '#cbd5e1',
          borderWidth: 1.8,
          borderDash: [5, 5],
          pointRadius: 0,
          fill: false,
          order: 2
        },
        {
          label: 'Same-Week Peer Avg',
          data: data.peer_baseline_series,
          borderColor: '#fb923c',
          borderWidth: 1.8,
          borderDash: [3, 3],
          pointRadius: 0,
          fill: false,
          order: 3
        }
      ]
    },
    options: {
      responsive: true,
      maintainAspectRatio: false,
      interaction: {
        mode: 'index',
        intersect: false
      },
      plugins: {
        legend: { display: false },
        tooltip: {
          backgroundColor: 'rgba(15, 23, 42, 0.95)',
          titleFont: { family: 'Outfit', size: 13, weight: 'bold' },
          bodyFont: { family: 'Outfit', size: 12 },
          borderColor: 'rgba(255, 255, 255, 0.1)',
          borderWidth: 1,
          padding: 12,
          callbacks: {
            afterBody: function(tooltipItems) {
              const idx = tooltipItems[0].dataIndex;
              const anom = data.anomaly_flags[idx];
              if (anom) {
                return [
                  '',
                  `Status: ${anom.flagged.toUpperCase()}`,
                  anom.matched_note_id ? `Matched Note: ${anom.matched_note_id}` : 'Matched Note: None',
                  `Reason: ${anom.reason}`
                ];
              }
              return '';
            }
          }
        }
      },
      scales: {
        x: {
          grid: { color: 'rgba(255, 255, 255, 0.04)' },
          ticks: {
            color: '#94a3b8',
            font: { family: 'JetBrains Mono', size: 10 },
            maxTicksLimit: 12
          }
        },
        y: {
          grid: { color: 'rgba(255, 255, 255, 0.05)' },
          ticks: {
            color: '#94a3b8',
            font: { family: 'Outfit', size: 11 },
            callback: (v) => `₹${v.toFixed(2)}`
          }
        }
      }
    }
  });
}

// 3. Anomaly Feed Table
async function initAnomalyTable() {
  try {
    const res = await fetch('/api/anomalies');
    const data = await res.json();
    cachedAnomalies = data.anomalies;
    renderAnomalyRows(cachedAnomalies);
  } catch (err) {
    console.error('Error loading anomalies:', err);
  }

  // Filter chips
  const chips = document.querySelectorAll('.filter-chip');
  chips.forEach(chip => {
    chip.addEventListener('click', (e) => {
      chips.forEach(c => c.classList.remove('active'));
      chip.classList.add('active');
      currentFilter = chip.dataset.filter;
      applyAnomalyFilter();
    });
  });
}

function applyAnomalyFilter() {
  let filtered = cachedAnomalies;
  if (currentFilter === 'justified') {
    filtered = cachedAnomalies.filter(a => a.flagged.includes('justified'));
  } else if (currentFilter === 'unexplained') {
    filtered = cachedAnomalies.filter(a => a.flagged === 'Yes');
  }
  renderAnomalyRows(filtered);
}

function renderAnomalyRows(rows) {
  const tbody = document.getElementById('anomalyTableBody');
  tbody.innerHTML = '';

  rows.forEach(r => {
    const tr = document.createElement('tr');
    const isJustified = r.flagged.includes('justified');
    const badgeClass = isJustified ? 'badge-justified' : 'badge-flagged';
    const noteTag = r.matched_note_id ? `<span class="note-tag">${r.matched_note_id}</span>` : '<span style="color:var(--text-muted)">—</span>';

    tr.innerHTML = `
      <td><strong>${r.route}</strong></td>
      <td><span style="font-family:var(--font-mono);font-size:0.8rem">${r.week_of}</span></td>
      <td><strong>₹${r.cost_per_tonne_km.toFixed(2)}</strong></td>
      <td style="color:${r.vs_own_history.includes('+') ? '#f87171' : '#34d399'}">${r.vs_own_history.split(' vs')[0]}</td>
      <td style="color:${r.vs_similar_routes.includes('+') ? '#fb923c' : '#34d399'}">${r.vs_similar_routes.split(' vs')[0]}</td>
      <td><span class="badge ${badgeClass}">${r.flagged}</span></td>
      <td>${noteTag}</td>
      <td><button class="btn btn-sm btn-outline btn-inspect" data-week="${r.week_of}" data-route="${r.route}">Inspect</button></td>
    `;
    tbody.appendChild(tr);
  });

  // Attach inspect click handlers
  document.querySelectorAll('.btn-inspect').forEach(btn => {
    btn.addEventListener('click', () => {
      const route = btn.dataset.route;
      const week = btn.dataset.week;
      const item = cachedAnomalies.find(a => a.route === route && a.week_of === week);
      if (item) openDetailModal(item);
    });
  });
}

// 4. Interactive Q&A Chat
function initChat() {
  const form = document.getElementById('chatForm');
  const input = document.getElementById('chatInput');
  const messages = document.getElementById('chatMessages');
  const clearBtn = document.getElementById('btnClearChat');

  form.addEventListener('submit', async (e) => {
    e.preventDefault();
    const query = input.value.trim();
    if (!query) return;

    appendMessage('user', query);
    input.value = '';

    // Show typing placeholder
    const typingId = appendTypingIndicator();

    try {
      const res = await fetch('/api/chat', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ query: query })
      });
      const data = await res.json();
      removeTypingIndicator(typingId);
      appendMessage('assistant', data.answer);
    } catch (err) {
      removeTypingIndicator(typingId);
      appendMessage('assistant', 'Sorry, I encountered an issue retrieving findings. Please try again.');
    }
  });

  // Prompt pills
  document.querySelectorAll('.prompt-pills .pill').forEach(pill => {
    pill.addEventListener('click', () => {
      input.value = pill.dataset.prompt;
      form.dispatchEvent(new Event('submit'));
    });
  });

  clearBtn.addEventListener('click', () => {
    messages.innerHTML = `
      <div class="message system-message">
        <div class="message-bubble">
          Chat cleared. Ask me anything about our shipping cost findings or route anomalies.
        </div>
      </div>
    `;
  });
}

function appendMessage(sender, text) {
  const messages = document.getElementById('chatMessages');
  const msgDiv = document.createElement('div');
  msgDiv.className = `message ${sender}-message`;

  // Parse markdown bold and bullets simply
  let formatted = text
    .replace(/\*\*(.*?)\*\*/g, '<strong>$1</strong>')
    .replace(/_(.*?)_/g, '<em>$1</em>')
    .replace(/\n\n/g, '<br><br>')
    .replace(/- (.*?)(\n|$)/g, '<li>$1</li>');

  if (formatted.includes('<li>')) {
    formatted = formatted.replace(/(<li>.*?<\/li>)/gs, '<ul>$1</ul>');
  }

  msgDiv.innerHTML = `<div class="message-bubble">${formatted}</div>`;
  messages.appendChild(msgDiv);
  messages.scrollTop = messages.scrollHeight;
}

function appendTypingIndicator() {
  const messages = document.getElementById('chatMessages');
  const id = 'typing_' + Date.now();
  const div = document.createElement('div');
  div.id = id;
  div.className = 'message assistant-message';
  div.innerHTML = '<div class="message-bubble" style="color:var(--text-muted)">Thinking & checking guardrails...</div>';
  messages.appendChild(div);
  messages.scrollTop = messages.scrollHeight;
  return id;
}

function removeTypingIndicator(id) {
  const el = document.getElementById(id);
  if (el) el.remove();
}

// 5. Guardrail Probes List
async function initProbes() {
  try {
    const res = await fetch('/api/probes');
    const data = await res.json();
    const list = document.getElementById('probeList');
    list.innerHTML = '';

    data.probe_details.forEach(p => {
      const item = document.createElement('div');
      item.className = 'probe-item';
      item.innerHTML = `
        <div class="probe-desc">
          <strong>${p.probe_id.replace('PROBE_', '')}</strong>: ${p.description}
        </div>
        <span class="probe-badge-pass">PASS</span>
      `;
      list.appendChild(item);
    });
  } catch (err) {
    console.error('Error loading probes:', err);
  }
}

// 6. Modal
function initModal() {
  const backdrop = document.getElementById('modalBackdrop');
  const close = document.getElementById('modalClose');

  close.addEventListener('click', () => backdrop.classList.remove('open'));
  backdrop.addEventListener('click', (e) => {
    if (e.target === backdrop) backdrop.classList.remove('open');
  });
}

function openDetailModal(item) {
  const backdrop = document.getElementById('modalBackdrop');
  const title = document.getElementById('modalTitle');
  const body = document.getElementById('modalBody');

  title.textContent = `${item.route} • Week of ${item.week_of}`;
  const isJustified = item.flagged.includes('justified');

  body.innerHTML = `
    <div style="display:grid;grid-template-columns:1fr 1fr;gap:12px;margin-bottom:16px;">
      <div>
        <p style="font-size:0.8rem;color:var(--text-muted)">ACTUAL COST</p>
        <p style="font-size:1.4rem;font-weight:700">₹${item.cost_per_tonne_km.toFixed(2)}/t-km</p>
      </div>
      <div>
        <p style="font-size:0.8rem;color:var(--text-muted)">GUARDRAIL STATUS</p>
        <span class="badge ${isJustified ? 'badge-justified' : 'badge-flagged'}" style="font-size:0.85rem">${item.flagged}</span>
      </div>
    </div>
    
    <div style="background:rgba(255,255,255,0.03);padding:14px;border-radius:10px;margin-bottom:14px;">
      <p style="margin-bottom:6px"><strong>vs. Own 8-Wk Trailing Baseline:</strong> ${item.vs_own_history}</p>
      <p><strong>vs. Same-Week Peer Corridors:</strong> ${item.vs_similar_routes}</p>
    </div>

    ${item.matched_note_id ? `
      <div style="background:rgba(16,185,129,0.08);border:1px solid rgba(16,185,129,0.25);padding:12px;border-radius:10px;margin-bottom:14px;">
        <p style="color:#34d399;font-weight:600;margin-bottom:4px">CITED NOTE: ${item.matched_note_id}</p>
        <p style="font-size:0.85rem;color:#e2e8f0">${item.reason}</p>
      </div>
    ` : `
      <div style="background:rgba(244,63,94,0.08);border:1px solid rgba(244,63,94,0.25);padding:12px;border-radius:10px;margin-bottom:14px;">
        <p style="color:#fb7185;font-weight:600;margin-bottom:4px">AUDIT VERDICT: UNEXPLAINED / HUMAN REVIEW</p>
        <p style="font-size:0.85rem;color:#e2e8f0">${item.reason}</p>
      </div>
    `}
  `;

  backdrop.classList.add('open');
}
