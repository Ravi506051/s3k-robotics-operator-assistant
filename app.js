const $ = selector => document.querySelector(selector);
const esc = value => String(value ?? '').replace(/[&<>"']/g, c => ({'&':'&amp;','<':'&lt;','>':'&gt;','"':'&quot;',"'":'&#39;'}[c]));
let state = { assets: [], events: [], actions: [], maintenance: [], metrics: {}, network_online: true };
let selectedEvent = null;

async function api(path, options = {}) {
  const response = await fetch(path, { ...options, headers: { 'Content-Type': 'application/json', ...(options.headers || {}) } });
  const data = await response.json();
  if (!response.ok) throw new Error(data.error || `Request failed (${response.status})`);
  return data;
}

function toast(message, bad = false) {
  const node = $('#toast'); node.textContent = message; node.style.background = bad ? '#974b3c' : '#244c3b'; node.classList.add('show');
  clearTimeout(toast.timer); toast.timer = setTimeout(() => node.classList.remove('show'), 3700);
}

function stateClass(value) { return value === 'Review trend' ? 'review' : value === 'Reporting' ? '' : 'gap'; }
function reading(value, unit) { return value === null || value === undefined ? '<b class="missing">No data</b>' : `<b>${Number(value).toFixed(1)} ${unit}</b>`; }

function renderAssets() {
  $('#asset-grid').innerHTML = state.assets.map(asset => `<article class="asset"><div class="asset-head"><span class="asset-id">${esc(asset.id)}</span><span class="state-pill ${stateClass(asset.display_state)}">${esc(asset.display_state)}</span></div><div class="asset-name">${esc(asset.name)}</div><div class="asset-location">${esc(asset.location)}</div><div class="readings"><div><span>TEMP</span>${reading(asset.temperature,'°C')}</div><div><span>VIBRATION</span>${reading(asset.vibration,'mm/s')}</div><div><span>CURRENT</span>${reading(asset.current,'A')}</div></div><div class="reading-note">Last signal ${Math.max(0,asset.age_seconds)}s ago · ${asset.display_state === 'Stale data' ? 'Do not treat as live' : 'Illustrative only'}</div></article>`).join('');
}

function renderEvents() {
  $('#event-list').innerHTML = state.events.slice(0, 7).map(event => `<div class="event"><span class="event-dot ${event.severity === 'Data gap' ? 'gap' : event.severity === 'Info' ? 'info' : ''}"></span><div class="event-body"><strong>${esc(event.asset)} · ${esc(event.kind)}</strong><p>${esc(event.message)}</p><small>${new Date(event.created_at).toLocaleString('en-IN')} · ${esc(event.status)}</small></div><button type="button" data-event="${event.id}" ${event.status !== 'Open' ? 'disabled' : ''}>${event.status === 'Open' ? 'Acknowledge' : 'Recorded'}</button></div>`).join('') || '<p class="panel-lead">No events recorded.</p>';
}

function renderMaintenance() {
  $('#maintenance-list').innerHTML = state.maintenance.map(item => `<div class="maintenance-item"><b>${esc(item.asset)}</b> ${esc(item.work)}<small>${new Date(item.completed_at).toLocaleDateString('en-IN')}</small></div>`).join('');
}

async function renderGuidance() {
  const data = await api(`/api/assets/${$('#guide-asset').value}/guidance`);
  $('#guide-body').innerHTML = `<p class="guide-status">${esc(data.asset)} · ${esc(data.display_state)}</p><ol class="guide-list">${data.checks.map((item,index) => `<li><b>${String(index+1).padStart(2,'0')}</b><span>${esc(item)}</span></li>`).join('')}</ol><div class="guide-maintenance"><strong>Recent maintenance</strong><br>${data.maintenance ? esc(data.maintenance.work) : 'No history in this demo.'}</div><p class="disclaimer">${esc(data.disclaimer)}</p>`;
}

async function refresh() {
  state = await api('/api/state');
  $('#network-pill').textContent = state.network_online ? '● Network connected' : '● Network gap';
  $('#network-pill').classList.toggle('offline', !state.network_online);
  $('#m-reporting').textContent = state.metrics.reporting;
  $('#m-events').textContent = state.metrics.open_events;
  $('#m-gaps').textContent = state.metrics.data_gaps;
  $('#m-ack').textContent = state.metrics.acknowledged;
  $('#last-refresh').textContent = `Viewed ${new Date().toLocaleTimeString('en-IN', { hour: '2-digit', minute: '2-digit' })}`;
  renderAssets(); renderEvents(); renderMaintenance(); await renderGuidance();
}

async function simulate(scenario) {
  try { await api('/api/simulate', { method: 'POST', body: JSON.stringify({ scenario }) }); await refresh(); toast('Fictional scenario recorded. Review the new state.'); }
  catch (error) { toast(error.message, true); }
}

$('#time').textContent = new Date().toLocaleDateString('en-IN', { day: '2-digit', month: 'long', year: 'numeric' });
$('#guide-asset').addEventListener('change', () => renderGuidance().catch(e => toast(e.message,true)));
$('.scenario-grid').addEventListener('click', event => { const button = event.target.closest('[data-scenario]'); if (button) simulate(button.dataset.scenario); });
$('#restore').addEventListener('click', () => simulate('restore_network'));
$('#event-list').addEventListener('click', event => {
  const button = event.target.closest('[data-event]'); if (!button || button.disabled) return;
  selectedEvent = Number(button.dataset.event);
  const item = state.events.find(row => row.id === selectedEvent);
  $('#ack-title').textContent = `Acknowledge ${item.asset} event`;
  $('#ack-message').textContent = item.message;
  $('#ack-dialog').showModal();
});
$('#close-ack').addEventListener('click', () => $('#ack-dialog').close());
$('#ack-form').addEventListener('submit', async event => {
  event.preventDefault();
  try { await api(`/api/events/${selectedEvent}/ack`, { method: 'POST', body: JSON.stringify(Object.fromEntries(new FormData(event.target))) }); $('#ack-dialog').close(); event.target.reset(); await refresh(); toast('Acknowledgment and operator note recorded.'); }
  catch (error) { toast(error.message, true); }
});
$('#ask-form').addEventListener('submit', async event => {
  event.preventDefault();
  try { const data = await api('/api/assistant', { method: 'POST', body: JSON.stringify({ question: $('#ask-input').value }) }); $('#answer').textContent = data.answer; }
  catch (error) { toast(error.message, true); }
});
refresh().catch(error => toast(`Could not load telemetry demo: ${error.message}`, true));
setInterval(() => refresh().catch(() => {}), 30_000);
