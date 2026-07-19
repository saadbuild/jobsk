/* ═══════════════════════════════════════════
   JOBSK — MAIN APP LOGIC (v3)
   Every "Save" button here now actually calls the
   backend and persists — see README for the full
   list of what changed from v2.
   ═══════════════════════════════════════════ */

/* ─── SIDEBAR (menu-button drawer) ──────── */
function openSidebar() {
  document.getElementById('sidebar')?.classList.add('open');
  document.getElementById('sidebarBackdrop')?.classList.add('open');
  document.getElementById('menuBtn')?.setAttribute('aria-expanded', 'true');
}
function closeSidebar() {
  document.getElementById('sidebar')?.classList.remove('open');
  document.getElementById('sidebarBackdrop')?.classList.remove('open');
  document.getElementById('menuBtn')?.setAttribute('aria-expanded', 'false');
}
function toggleSidebar() {
  const sb = document.getElementById('sidebar');
  if (sb && sb.classList.contains('open')) closeSidebar(); else openSidebar();
}

/* ─── SCREEN NAVIGATION ─────────────────── */
function go(id, btn) {
  document.querySelectorAll('.screen').forEach(s => s.classList.remove('active'));
  document.querySelectorAll('.nav-item').forEach(b => b.classList.remove('active'));
  const s = document.getElementById('s-' + id);
  if (s) s.classList.add('active');
  if (btn) btn.classList.add('active');
  closeSidebar();
  const mainEl = document.querySelector('.main');
  if (mainEl) mainEl.scrollTop = 0;
}

/* ─── TOGGLE FILTER GROUPS ──────────────── */
function tgl(btn, groupId) {
  document.querySelectorAll('#' + groupId + ' .tbtn').forEach(b => b.classList.remove('on'));
  btn.classList.add('on');
}

/* ─── PLATFORM FILTER TABS (Platforms screen) ── */
function fp(cat, btn) {
  document.querySelectorAll('.ftab').forEach(b => b.classList.remove('on'));
  btn.classList.add('on');
  document.querySelectorAll('.pcard').forEach(card => {
    card.classList.toggle('hidden', !(cat === 'all' || card.dataset.c === cat));
  });
}

/* ─── SELECT ALL SOURCES (Search screen) ── */
function selectAll() {
  const boxes = document.querySelectorAll('#ppicker input[type=checkbox]');
  const allChecked = Array.from(boxes).every(b => b.checked);
  boxes.forEach(b => { b.checked = !allChecked; });
  countPlatforms();
  const btn = document.getElementById('selAllBtn');
  if (btn) btn.textContent = allChecked ? 'Select all' : 'Deselect all';
}

function countPlatforms() {
  const count = document.querySelectorAll('#ppicker input:checked').length;
  const msg = document.getElementById('pcount');
  if (msg) msg.textContent = count === 0
    ? '0 sources selected — select at least one'
    : count + ' source' + (count > 1 ? 's' : '') + ' selected';
}

function updRate() {
  const min = parseInt(document.getElementById('rmin').value);
  const max = parseInt(document.getElementById('rmax').value);
  const display = document.getElementById('rval');
  if (display) display.textContent = '$' + Math.min(min, max) + ' — $' + Math.max(min, max) + '/hr';
}

function qs(text) {
  const inp = document.getElementById('sq');
  if (inp) { inp.value = text; inp.focus(); }
}

/* ─── CURRENT USER / AUTH HEADERS ────────── */
function currentUser() {
  try { return JSON.parse(localStorage.getItem('jobsk_user') || 'null'); }
  catch (e) { return null; }
}
function authHeaders() {
  const token = localStorage.getItem('jobsk_token') || '';
  return { 'Content-Type': 'application/json', 'Authorization': 'Bearer ' + token };
}

/* ─── LOAD REAL LOGGED-IN USER + VERIFY SESSION ── */
async function loadCurrentUser() {
  const user = currentUser();
  if (!user) return null;

  const nameEl = document.getElementById('userName');
  const emailEl = document.getElementById('userEmail');
  const avEl = document.getElementById('userAvatar');
  if (nameEl) nameEl.textContent = user.name || 'User';
  if (emailEl) emailEl.textContent = user.email || '';
  if (avEl) avEl.textContent = (user.name || 'U').split(' ').map(w => w[0]).join('').toUpperCase().slice(0, 2);

  const greet = document.getElementById('homeGreeting');
  if (greet) {
    const hour = new Date().getHours();
    const part = hour < 12 ? 'morning' : hour < 18 ? 'afternoon' : 'evening';
    const firstName = (user.name || 'there').split(' ')[0];
    greet.textContent = `Good ${part}, ${firstName} 👋`;
  }

  // Confirm the server still recognizes this session. If not — most
  // likely the backend's database was reset (see README, "why did my
  // account disappear") — sign out cleanly instead of pretending to
  // still be logged in with data that no longer exists server-side.
  try {
    const res = await fetch(BACKEND_URL + '/api/auth/verify', { headers: authHeaders() });
    if (res.status === 401) {
      showToast('Your session is no longer valid — please sign in again', 'error');
      setTimeout(signOut, 1400);
      return null;
    }
    const data = await res.json();
    if (data.user) {
      localStorage.setItem('jobsk_user', JSON.stringify(data.user));
      populateSettingsForm(data.user);
    }
  } catch (e) {
    console.log('Could not verify session — backend may be offline:', e);
  }

  return user;
}

function populateSettingsForm(user) {
  const set = (id, val) => { const el = document.getElementById(id); if (el) el.value = val ?? ''; };
  set('setName', user.name);
  set('setEmail', user.email);
  set('setSkills', user.skills);
  set('setAlertKeywords', user.alert_keywords);
  set('setAlertMinRate', user.alert_min_rate ?? 0);
  set('setAlertPhone', user.alert_phone);
  set('setAgentMinRate', user.agent_min_rate ?? 0);
  set('setAgentJobType', user.agent_job_types || 'all');
  set('setScanMinutes', user.agent_scan_minutes ?? 1);
  const enabledSel = document.getElementById('setAlertEnabled');
  if (enabledSel) enabledSel.value = String(!!user.alerts_enabled);
  const smsSel = document.getElementById('setAlertSms');
  if (smsSel) smsSel.value = String(!!user.alert_sms_enabled);
}

/* ─── USER DROPDOWN MENU ────────────────── */
function toggleUserMenu() {
  const dd = document.getElementById('userDropdown');
  if (dd) dd.style.display = dd.style.display === 'none' ? 'flex' : 'none';
}

/* ─── SIGN OUT ───────────────────────────── */
function signOut() {
  localStorage.removeItem('jobsk_token');
  localStorage.removeItem('jobsk_user');
  localStorage.removeItem('jobsk_login_time');
  window.location.href = 'pages/login.html';
}

/* ─── JOB RENDERING (shared by Home + Search) ── */
function jobCardHTML(job) {
  const initials = (job.platform || '?').slice(0, 2).toUpperCase();
  const match = job.match ? `<span class="job-match">${job.match} match</span>` : '';
  const company = job.company ? `<span>${escapeHTML(job.company)}</span>` : '';
  return `
    <div class="job-card">
      <div class="job-logo" style="background:linear-gradient(135deg,#6c63ff,#8b7fff)">${initials}</div>
      <div class="job-info">
        <div class="job-title">${escapeHTML(job.title)}</div>
        <div class="job-meta">
          <span>${escapeHTML(job.platform || '')}</span>
          ${company}
          <span class="job-rate">${escapeHTML(job.rate || 'Rate not specified')}</span>
          <span>${escapeHTML(job.type || '')}</span>
          ${job.posted ? `<span>${escapeHTML(job.posted)}</span>` : ''}
          ${match}
        </div>
      </div>
      <button class="btn-apply" onclick="window.open('${job.url}','_blank')">Apply →</button>
    </div>`;
}
function escapeHTML(s) {
  return String(s ?? '').replace(/[&<>"']/g, c => ({'&':'&amp;','<':'&lt;','>':'&gt;','"':'&quot;',"'":'&#39;'}[c]));
}

function renderJobList(jobs, listEl, countEl) {
  if (!listEl) return;
  if (countEl) countEl.textContent = jobs.length;
  if (jobs.length === 0) {
    listEl.innerHTML = '<div style="padding:20px;color:#94a3b8;font-size:13px">No jobs found — try different keywords, widen your rate range, or select more sources.</div>';
    return;
  }
  listEl.innerHTML = jobs.map(jobCardHTML).join('');
}

/* ─── SEARCH JOBS (real backend, real sources) ── */
async function doSearch() {
  const q = (document.getElementById('sq') || {}).value || '';
  const resultsBox = document.getElementById('results');
  const rlist = document.getElementById('rlist');
  const rcnt = document.getElementById('rcnt');
  if (!resultsBox) return;

  const platforms = Array.from(document.querySelectorAll('#ppicker input:checked')).map(i => i.value);
  const rmin = parseInt(document.getElementById('rmin')?.value || 0);
  const rmax = parseInt(document.getElementById('rmax')?.value || 100000);
  const jobTypeBtn = document.querySelector('#jg .tbtn.on');
  const jobType = jobTypeBtn ? jobTypeBtn.textContent.trim().toLowerCase() : 'all types';
  const jobTypeParam = jobType.includes('all') ? 'all' : jobType.includes('remote') ? 'remote'
    : jobType.includes('hourly') ? 'hourly' : jobType.includes('fixed') ? 'fixed' : jobType.includes('full') ? 'full-time' : 'all';

  resultsBox.style.display = 'block';
  rlist.innerHTML = '<div style="padding:14px;color:#64748b;font-size:13px;display:flex;align-items:center;gap:8px"><div class="spin"></div>Searching real job sources…</div>';

  const user = currentUser();

  try {
    const res = await fetch(BACKEND_URL + '/api/search', {
      method: 'POST',
      headers: authHeaders(),
      body: JSON.stringify({
        query: q, platforms, min_rate: Math.min(rmin, rmax), max_rate: Math.max(rmin, rmax),
        job_type: jobTypeParam, email: user ? user.email : null,
      }),
    });
    const data = await res.json();
    renderJobList(data.jobs || [], rlist, rcnt);
    refreshHomeStats();
    loadSearchHistory();
  } catch (e) {
    rlist.innerHTML = '<div style="padding:14px;color:#dc2626;font-size:13px">Could not reach the backend at ' + BACKEND_URL + '. Is it running? (see README)</div>';
  }
}

/* ─── HOME JOBS ──────────────────────────── */
async function loadHomeJobs() {
  const list = document.getElementById('homeJobs');
  if (!list) return;
  const user = currentUser();
  if (!user) return;

  list.innerHTML = '<div style="padding:14px;color:#64748b;font-size:13px;display:flex;align-items:center;gap:8px"><div class="spin"></div>Loading…</div>';

  try {
    const res = await fetch(BACKEND_URL + '/api/cv/auto-search', {
      method: 'POST', headers: authHeaders(),
      body: JSON.stringify({ email: user.email, platforms: [] }),
    });
    const data = await res.json();
    if (data.jobs && data.jobs.length > 0) {
      renderJobList(data.jobs.slice(0, 5), list, null);
    } else {
      list.innerHTML = '<div style="padding:20px;color:#94a3b8;font-size:13px">' +
        (data.message === 'No CV uploaded yet'
          ? 'Upload your CV to get personalized matches here — or run a manual search anytime.'
          : 'No matches yet — try running a search.') + '</div>';
    }
  } catch (e) {
    list.innerHTML = '<div style="padding:20px;color:#94a3b8;font-size:13px">Could not reach the backend.</div>';
  }
}

/* ─── HOME STATS (real numbers, not hardcoded) ── */
async function refreshHomeStats() {
  const user = currentUser();
  if (!user) return;

  try {
    const [historyRes, notifRes] = await Promise.all([
      fetch(BACKEND_URL + '/api/search/history?email=' + encodeURIComponent(user.email)),
      fetch(BACKEND_URL + '/api/notifications', { headers: authHeaders() }),
    ]);
    const historyData = await historyRes.json();
    const notifData = await notifRes.json();

    const searches = historyData.history || [];
    const notifs = notifData.notifications || [];
    const unread = notifs.filter(n => !n.read).length;

    setText('statSearches', searches.length);
    setText('statNotifs', unread);
    setText('statNotifsSub', unread === 1 ? 'Unread' : 'Unread');

    const navSub = document.getElementById('navNotifSub');
    const navBadge = document.getElementById('navNotifBadge');
    if (navSub) navSub.textContent = unread + (unread === 1 ? ' new' : ' new');
    if (navBadge) { navBadge.textContent = unread; navBadge.style.display = unread > 0 ? 'inline-flex' : 'none'; }
  } catch (e) { /* backend offline — leave last-known values */ }

  const skills = (user.last_cv_skills && Array.isArray(user.last_cv_skills)) ? user.last_cv_skills : null;
}

function setText(id, val) {
  const el = document.getElementById(id);
  if (el) el.textContent = val;
}

/* ─── AGENT TIMER (visual countdown to next auto-refresh) ── */
function startTimer() {
  const el = document.getElementById('timer');
  if (!el) return;
  let secs = Math.floor(AUTO_REFRESH_MS / 1000);
  setInterval(() => {
    secs--;
    if (secs < 0) secs = Math.floor(AUTO_REFRESH_MS / 1000);
    const m = Math.floor(secs / 60);
    const s = secs % 60;
    el.textContent = 'Next scan in ' + m + ':' + String(s).padStart(2, '0');
  }, 1000);
}

/* ─── CHATBOT ────────────────────────────── */
function addMsg(text, role, isTyping = false) {
  const msgs = document.getElementById('chatMsgs');
  if (!msgs) return;
  const div = document.createElement('div');
  div.className = 'cmsg ' + role;
  const bbl = document.createElement('div');
  bbl.className = 'cmsg-bbl' + (isTyping ? ' typing' : '');
  bbl.innerHTML = escapeHTML(text).replace(/\n/g, '<br/>');
  if (isTyping) bbl.id = 'typing-bubble';
  div.appendChild(bbl);
  msgs.appendChild(div);
  msgs.scrollTop = msgs.scrollHeight;
  return bbl;
}

function sendChat() {
  const inp = document.getElementById('chatInp');
  if (!inp) return;
  const text = inp.value.trim();
  if (!text) return;
  inp.value = '';
  addMsg(text, 'user');
  addMsg('Thinking...', 'bot', true);

  setTimeout(async () => {
    const typing = document.getElementById('typing-bubble');
    if (typing) typing.closest('.cmsg').remove();
    try {
      const res = await fetch(BACKEND_URL + '/api/chat', {
        method: 'POST', headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ message: text }),
      });
      const data = await res.json();
      addMsg(data.response || "Sorry, I couldn't reach the server.", 'bot');
    } catch (e) {
      addMsg("Could not reach the backend at " + BACKEND_URL + ". Is it running?", 'bot');
    }
  }, 500);
}

function clearChat() {
  const msgs = document.getElementById('chatMsgs');
  if (msgs) msgs.innerHTML = '<div class="cmsg bot"><div class="cmsg-bbl">Chat cleared. How can I help you?</div></div>';
}
function askT(question) {
  const inp = document.getElementById('chatInp');
  if (inp) { inp.value = question; sendChat(); }
}

/* ─── CV UPLOAD (real backend parsing — PDF/DOCX/TXT) ── */
function cvDropHandler(event) {
  event.preventDefault();
  const zone = document.getElementById('cvDrop');
  if (zone) zone.classList.remove('dv');
  const file = event.dataTransfer.files[0];
  if (file) uploadCV(file);
}
function cvHandler(event) {
  const file = event.target.files[0];
  if (file) uploadCV(file);
}
function cvMainDrop(event) {
  event.preventDefault();
  const zone = document.getElementById('cvZone');
  if (zone) zone.classList.remove('dv');
  const file = event.dataTransfer.files[0];
  if (file) uploadCV(file);
}
function cvMainFile(event) {
  const file = event.target.files[0];
  if (file) uploadCV(file);
}

async function uploadCV(file) {
  const user = currentUser();
  if (!user) { showToast('Please sign in first', 'error'); return; }

  showToast('Uploading ' + file.name + ' — reading and extracting skills…', 'info');

  const form = new FormData();
  form.append('cv', file);
  form.append('email', user.email);

  try {
    const res = await fetch(BACKEND_URL + '/api/cv/analyze', { method: 'POST', body: form });
    const data = await res.json();
    if (!data.success) { showToast(data.message || 'Could not read that file', 'error'); return; }

    showToast(`${data.skill_count} skill${data.skill_count === 1 ? '' : 's'} detected from your CV`, 'success');
    renderCvResults(data);
    loadHomeJobs();
    refreshHomeStats();
  } catch (e) {
    showToast('Could not reach the backend at ' + BACKEND_URL, 'error');
  }
}

function renderCvResults(data) {
  const row = document.getElementById('cvSkillsRow');
  if (row) {
    row.innerHTML = data.skills_detected.length
      ? data.skills_detected.map(s => `<span class="sk" style="background:#eef2ff;color:#4338ca">${escapeHTML(s)}</span>`).join('')
      : '<span class="sk" style="background:#f1f5f9;color:#64748b">No known skills detected — try a more detailed CV</span>';
  }
  setText('cvScoreNum', data.match_score + '%');
  const fill = document.getElementById('cvScoreFill');
  if (fill) fill.style.width = data.match_score + '%';
  setText('cvScoreTip', data.skill_count > 0
    ? `${data.skill_count} skills detected. These now drive your automatic job matching and alerts.`
    : 'No recognized skills found — try uploading a CV with clearer skill/tool names.');
}

/* ─── SETTINGS: PROFILE (real save — was fake in v2) ── */
async function saveProfile() {
  const name = document.getElementById('setName').value.trim();
  const email = document.getElementById('setEmail').value.trim();
  const skills = document.getElementById('setSkills').value.trim();
  const password = document.getElementById('setPassword').value;

  try {
    const res = await fetch(BACKEND_URL + '/api/user/profile', {
      method: 'PUT', headers: authHeaders(),
      body: JSON.stringify({ name, email, skills, password }),
    });
    const data = await res.json();
    if (data.success) {
      localStorage.setItem('jobsk_user', JSON.stringify(data.user));
      document.getElementById('setPassword').value = '';
      loadCurrentUser();
      showToast('Profile saved', 'success');
    } else {
      showToast(data.message || 'Could not save profile', 'error');
    }
  } catch (e) {
    showToast('Could not reach the backend — profile NOT saved', 'error');
  }
}

/* ─── SETTINGS: AGENT PREFS (real save) ── */
async function saveAgentPrefs() {
  const min_rate = parseInt(document.getElementById('setAgentMinRate').value || 0);
  const job_types = document.getElementById('setAgentJobType').value;
  const scan_minutes = parseInt(document.getElementById('setScanMinutes').value || 1);

  try {
    const res = await fetch(BACKEND_URL + '/api/user/agent-prefs', {
      method: 'PUT', headers: authHeaders(),
      body: JSON.stringify({ min_rate, job_types, scan_minutes }),
    });
    const data = await res.json();
    if (data.success) {
      showToast('Agent settings saved', 'success');
    } else {
      showToast(data.message || 'Could not save agent settings', 'error');
    }
  } catch (e) {
    showToast('Could not reach the backend — agent settings NOT saved', 'error');
  }
}

/* ─── ALERTS: SAVE (real save, incl. optional SMS) ── */
async function saveAlertSettings() {
  const keywords = document.getElementById('setAlertKeywords').value.trim();
  const min_rate = parseInt(document.getElementById('setAlertMinRate').value || 0);
  const enabled = document.getElementById('setAlertEnabled').value === 'true';
  const sms_enabled = document.getElementById('setAlertSms').value === 'true';
  const phone = document.getElementById('setAlertPhone').value.trim();

  try {
    const res = await fetch(BACKEND_URL + '/api/user/alerts', {
      method: 'PUT', headers: authHeaders(),
      body: JSON.stringify({ keywords, min_rate, enabled, sms_enabled, phone }),
    });
    const data = await res.json();
    if (data.success) {
      showToast('Alert settings saved', 'success');
    } else {
      showToast(data.message || 'Could not save alert settings', 'error');
    }
  } catch (e) {
    showToast('Could not reach the backend — alert settings NOT saved', 'error');
  }
}

/* ─── SEARCH HISTORY (real load + real delete) ── */
async function loadSearchHistory() {
  const user = currentUser();
  const list = document.getElementById('historyList');
  if (!user || !list) return;

  try {
    const res = await fetch(BACKEND_URL + '/api/search/history?email=' + encodeURIComponent(user.email));
    const data = await res.json();
    renderHistory(data.history || []);
  } catch (e) { /* keep whatever's already shown */ }
}

function renderHistory(history) {
  const list = document.getElementById('historyList');
  if (!list) return;
  if (history.length === 0) {
    list.innerHTML = '<div class="hist-row"><div class="hist-info"><div class="hist-query">No searches yet</div><div class="hist-meta">Run a search to see it appear here</div></div></div>';
    return;
  }
  list.innerHTML = history.map(item => {
    const date = new Date(item.timestamp);
    return `
      <div class="hist-row">
        <div class="hist-icon">🔍</div>
        <div class="hist-info">
          <div class="hist-query">"${escapeHTML(item.query || 'Auto-search')}"</div>
          <div class="hist-meta">${(item.platforms || []).join(', ') || 'All sources'} · ${item.result_count} results found</div>
        </div>
        <div class="hist-time">${date.toLocaleDateString()}, ${date.toLocaleTimeString([], {hour:'2-digit',minute:'2-digit'})}</div>
      </div>`;
  }).join('');
}

async function clearHistory() {
  try {
    const res = await fetch(BACKEND_URL + '/api/search/history', { method: 'DELETE', headers: authHeaders() });
    const data = await res.json();
    if (data.success) {
      renderHistory([]);
      showToast('History cleared', 'success');
      refreshHomeStats();
    } else {
      showToast('Could not clear history', 'error');
    }
  } catch (e) {
    showToast('Could not reach the backend', 'error');
  }
}

/* ─── NOTIFICATIONS (real — was 100% hardcoded fake data) ── */
async function loadNotifications() {
  const list = document.getElementById('notifList');
  const user = currentUser();
  if (!user) return;

  try {
    const res = await fetch(BACKEND_URL + '/api/notifications', { headers: authHeaders() });
    const data = await res.json();
    const notifs = data.notifications || [];
    if (list) renderNotifications(notifs);
    renderAlertList(notifs.filter(n => n.kind === 'match'));
  } catch (e) { /* leave as-is */ }
}

function renderAlertList(matchNotifs) {
  const list = document.getElementById('alertList');
  if (!list) return;
  if (matchNotifs.length === 0) {
    list.innerHTML = '<div class="alert-row"><div class="al-info"><div class="al-title">No alerts sent yet</div><div class="al-meta">Upload a CV and enable alerts to get started</div></div></div>';
    return;
  }
  list.innerHTML = matchNotifs.map(n => `
    <div class="alert-row">
      <div class="al-dot" style="background:#6c63ff"></div>
      <div class="al-info">
        <div class="al-title">${escapeHTML(n.title)}</div>
        <div class="al-meta">${escapeHTML(n.body)} · ${new Date(n.created_at).toLocaleString()}</div>
      </div>
      <span class="al-badge">Sent</span>
    </div>`).join('');
}

function notifIcon(kind) {
  return { match: '🎯', alert_sent: '📧', cv: '📄', info: '🔔' }[kind] || '🔔';
}

function renderNotifications(notifs) {
  const list = document.getElementById('notifList');
  if (!list) return;
  if (notifs.length === 0) {
    list.innerHTML = '<div class="nitem"><div class="ni-body"><div class="ni-t">No notifications yet</div><div class="ni-p">Upload a CV and run a search to start generating real activity here.</div></div></div>';
    return;
  }
  list.innerHTML = notifs.map(n => `
    <div class="nitem${n.read ? '' : ' new'}">
      <div class="ni-icon2" style="background:#eef2ff;color:#6c63ff;font-size:16px;display:flex;align-items:center;justify-content:center">${notifIcon(n.kind)}</div>
      <div class="ni-body">
        <div class="ni-t">${escapeHTML(n.title)}</div>
        <div class="ni-p">${escapeHTML(n.body)}</div>
        <div class="ni-time">${new Date(n.created_at).toLocaleString()}</div>
      </div>
      ${n.read ? '' : '<div class="new-dot2"></div>'}
    </div>`).join('');
}

async function markAllRead() {
  try {
    const res = await fetch(BACKEND_URL + '/api/notifications/read', { method: 'POST', headers: authHeaders() });
    const data = await res.json();
    if (data.success) {
      loadNotifications();
      refreshHomeStats();
      showToast('All marked as read', 'success');
    }
  } catch (e) {
    showToast('Could not reach the backend', 'error');
  }
}

/* ─── AUTO-REFRESH (default: every 1 minute) ──
   This nudges an immediate check while the tab is open. The real
   always-on version (works even with the tab closed) runs server-side
   in backend/scheduler.py — see README for what that actually requires
   on a free host.
────────────────────────────────────────── */
let autoRefreshInterval = null;

function startAutoRefresh() {
  runAutoRefreshSearch();
  autoRefreshInterval = setInterval(runAutoRefreshSearch, AUTO_REFRESH_MS);
}

async function runAutoRefreshSearch() {
  const user = currentUser();
  if (!user) return;
  loadHomeJobs();
  refreshHomeStats();
  loadNotifications();
}

/* ─── GUIDE MODAL DATA ───────────────────── */
const GUIDES = {
  fiverr: {
    title: '🟢 Complete Fiverr Guide — Get Your First Order',
    html: `
      <h3>What is Fiverr?</h3>
      <p>Fiverr is a marketplace where you sell "gigs" — fixed services starting from $5. Buyers come to you through search. You don't bid; you create a service and clients find you.</p>
      <h3>Step 1: Create your account</h3>
      <ul><li>Go to fiverr.com → click "Become a Seller"</li><li>Use a professional email and your real name</li><li>Upload a clear, friendly profile photo — face visible</li><li>Write a bio explaining your skills and experience</li></ul>
      <h3>Step 2: Create your first gig</h3>
      <ul><li>Title: "I will [specific action] for [client type]" — be very specific</li><li>Use all 5 allowed tags with words buyers actually search</li><li>Pricing: $5–15 basic / $25–50 standard / $75–150 premium</li><li>Description: explain exactly what you deliver, timeline, what you need from buyer</li></ul>
      <div class="modal-tip">💡 Good title: "I will build a Python web scraper for any website" — Bad title: "I will code for you"</div>
      <h3>Step 3: Get your first orders</h3>
      <ul><li>Check "Buyer Requests" daily — clients post what they need</li><li>Share your gig link on LinkedIn, WhatsApp groups, Facebook groups</li><li>Ask 2–3 contacts to order something small to get your first reviews</li><li>Respond to every message within 1 hour — response rate affects ranking</li></ul>
      <h3>Step 4: Deliver and grow</h3>
      <ul><li>Always deliver before the deadline — even 1 hour early is great</li><li>Deliver slightly more than promised — a small bonus goes a long way</li><li>After delivery: "If you're happy, a 5-star review would mean a lot to my profile!"</li><li>After 10 reviews: raise your price by 20%. After 50 reviews: you can double rates.</li></ul>
    `
  },
  upwork: {
    title: '🟡 Complete Upwork Guide — Win Your First Contract',
    html: `
      <h3>What is Upwork?</h3>
      <p>Upwork is the world's largest freelancing platform. Clients post jobs, you send proposals, clients choose who to hire. Unlike Fiverr, you go to the client — not the other way around.</p>
      <h3>Step 1: Build a strong profile</h3>
      <ul><li>Professional photo — bright background, clear face</li><li>Title: be specific — "Python & Machine Learning Developer" not just "Developer"</li><li>Overview: first 2 lines are shown before "Read More" — make them excellent</li><li>Add all relevant skills, portfolio samples, take skills tests</li></ul>
      <h3>Step 2: Find the right jobs</h3>
      <ul><li>Search for jobs under $500 first — easier to win, builds your history</li><li>Filter by "Payment Verified" clients</li><li>Look for clients with good hire rates (shown on job post)</li><li>New clients with 0 hires can be good — less competition</li></ul>
      <h3>Step 3: Write proposals that win</h3>
      <div class="modal-tip">"I noticed you need [specific thing from their post]. I built something similar for [brief example] and can deliver [their goal] within [timeline].<br/><br/>My approach: [2–3 sentences on your plan].<br/><br/>Quick question: [relevant question about their project]."</div>
      <h3>Step 4: Build your reputation</h3>
      <ul><li>Start with fixed-price contracts — easier to agree on scope</li><li>Communicate every 2 days minimum — clients love updates</li><li>After $1,000 earned + 90% rating: "Top Rated" badge — much easier to win jobs</li><li>Raise your rate by $5/hr after every 5 completed contracts</li></ul>
    `
  },
  linkedin: {
    title: '🔵 Complete LinkedIn Guide — Get Hired by Recruiters',
    html: `
      <h3>Why LinkedIn matters</h3>
      <p>87% of recruiters use LinkedIn to find candidates. A good profile works for you 24/7 — even when you're not actively applying anywhere.</p>
      <h3>Step 1: Optimise your profile</h3>
      <ul><li>Photo: professional, clear face — profiles with photos get 21x more views</li><li>Banner: use a free Canva template to stand out</li><li>Headline: "Python Developer | Machine Learning | Open to Remote Work"</li><li>About: 150 words — who you are, what you do, what you're looking for</li></ul>
      <h3>Step 2: Turn on "Open to Work"</h3>
      <ul><li>Go to your profile → "Open to" → "Finding a new job"</li><li>Select job titles, locations, and work types you want</li><li>Choose whether to show to all members or just recruiters</li></ul>
      <h3>Step 3: Build your network</h3>
      <ul><li>Connect with 50 people in your first week — classmates, alumni, coworkers</li><li>Always add a short personal note when connecting — doubles acceptance rate</li><li>Post once a week — even 2 paragraphs gets visibility</li></ul>
      <h3>Step 4: Message recruiters directly</h3>
      <div class="modal-tip">"Hi [Name], I saw you recruit for [company]. I'm a [skill] developer with [X years] experience, currently open to [role type]. Would a brief call make sense? Thank you."</div>
    `
  },
  freelancer: {
    title: '🔵 Complete Freelancer.com Guide',
    html: `
      <h3>What is Freelancer.com?</h3>
      <p>One of the oldest freelancing platforms. You bid on projects clients post. Similar to Upwork but with a different fee structure and a more competitive bidding environment.</p>
      <h3>Step 1: Set up your profile</h3>
      <ul><li>Complete your profile fully — verified profiles get more visibility</li><li>Take their skills tests — scores show next to your name on bids</li><li>Get your identity verified — increases client trust significantly</li><li>Add portfolio with real examples of your work</li></ul>
      <h3>Step 2: Find good projects</h3>
      <ul><li>Filter by "Recruiter" projects — agencies with regular work</li><li>Look for projects with fewer than 15 bids — easier to win</li><li>Avoid very low-budget projects ($5–10) unless just starting</li><li>The "Contest" section lets you win by submitting work — great for designers</li></ul>
      <h3>Step 3: Write winning bids</h3>
      <ul><li>Reference something specific from the project description</li><li>Propose a clear timeline and deliverables</li><li>Bid slightly above the budget average — too cheap looks suspicious</li><li>Ask one relevant question to start a conversation</li></ul>
      <h3>Step 4: Fees and payments</h3>
      <ul><li>Freelancer takes 10% of earnings (minimum $5 per project)</li><li>Always use Milestone Payments — never work without a funded milestone</li><li>Request payment in stages for larger projects</li></ul>
    `
  },
  cv: {
    title: '📄 How to Make a Perfect CV',
    html: `
      <h3>Why your CV structure matters</h3>
      <p>A CV is scanned by ATS software before it reaches a human, and gets about 6 seconds of human attention after that. These rules help it pass both filters.</p>
      <h3>Section 1: Contact and header</h3>
      <ul><li>Full name (large, at the top)</li><li>Email, phone, LinkedIn URL, city and country</li><li>Portfolio or GitHub link if you have one</li></ul>
      <h3>Section 2: Professional summary (2–3 lines)</h3>
      <div class="modal-tip">"Python developer with 3 years of experience in machine learning and data analysis. Built models deployed to 50,000+ users. Looking for remote freelance ML engineering work."</div>
      <h3>Section 3: Skills — list format</h3>
      <ul><li>List your top 8–12 technical skills clearly</li><li>Use exact words from job descriptions — ATS software and this app's own matcher both look for exact keyword overlap</li><li>Group them: Languages / Frameworks / Tools / Soft Skills</li></ul>
      <h3>Section 4: Work experience</h3>
      <ul><li>Job title, Company, Dates, Location</li><li>3–5 bullet points per job</li><li>Format: "Did [X action] which resulted in [Y outcome with numbers]"</li><li>Example: "Reduced model inference time by 40% using quantization"</li></ul>
      <h3>Section 5: Projects (if no experience)</h3>
      <ul><li>List 2–3 personal or academic projects</li><li>Include tech stack and what the project does</li><li>Add a GitHub link so employers can see actual code</li></ul>
      <h3>Format rules</h3>
      <ul><li>Font: Arial or Calibri, size 10–12pt</li><li>Length: 1 page if under 5 years experience, 2 pages max</li><li>Save as PDF — never send .doc or .docx</li><li>File name: "FirstName-LastName-CV.pdf"</li></ul>
      <div class="modal-tip">💡 Tailor your CV for each application — swap in keywords from the specific job description. One tailored CV beats ten generic ones every time.</div>
    `
  },
  proposal: {
    title: '✍️ Write Winning Proposals',
    html: `
      <h3>Why most proposals fail</h3>
      <p>90% of proposals start with "Dear Sir/Madam, I am writing to apply..." — clients stop reading immediately. The goal is to prove you read the job post and understand the client's specific problem.</p>
      <h3>The 5-part winning structure</h3>
      <h3>Part 1: Hook (first 2 lines)</h3>
      <div class="modal-tip">"I noticed you need a sentiment analysis model for 50,000 customer reviews — I built exactly this for a retail company last quarter, cutting their analysis time from 3 days to 4 hours."</div>
      <h3>Part 2: Your approach (3–5 lines)</h3>
      <p>Describe exactly HOW you will solve their problem. Not what tools you know — what you will do for them specifically.</p>
      <h3>Part 3: Relevant proof (2–3 lines)</h3>
      <p>Mention 1–2 relevant past projects. If you are new, mention a personal project with a GitHub link.</p>
      <h3>Part 4: Ask a smart question</h3>
      <div class="modal-tip">"Quick question: is the model only for English reviews, or does it need to handle other languages too? This affects the architecture significantly."</div>
      <h3>Part 5: Clear call to action</h3>
      <p>"Happy to jump on a 15-minute call this week. What works for your schedule?"</p>
      <h3>Things to never do</h3>
      <ul><li>Never copy-paste the same proposal to multiple clients</li><li>Never list all your skills without connecting them to the project</li><li>Never be too long — 150–250 words is the sweet spot</li><li>Never start with "Dear Sir" or "I am writing to apply"</li><li>Never submit with spelling mistakes — proofread before sending</li></ul>
    `
  }
};

function openGuide(type) {
  const guide = GUIDES[type];
  if (!guide) return;
  const modal = document.getElementById('modal');
  const body = document.getElementById('modal-body');
  body.innerHTML = '<h2>' + guide.title + '</h2>' + guide.html;
  modal.classList.add('open');
  document.body.style.overflow = 'hidden';
}
function closeModal(event) {
  const modal = document.getElementById('modal');
  if (event.target === modal) {
    modal.classList.remove('open');
    document.body.style.overflow = '';
  }
}
function closeModalDirect() {
  document.getElementById('modal').classList.remove('open');
  document.body.style.overflow = '';
}
document.addEventListener('keydown', e => {
  if (e.key === 'Escape') closeModalDirect();
});

/* ─── TOAST ──────────────────────────────── */
function showToast(message, type = 'info') {
  const icons = { success: '✅', error: '❌', info: '💡' };
  const container = document.getElementById('toasts');
  if (!container) return;
  const toast = document.createElement('div');
  toast.className = 'toast ' + type;
  toast.innerHTML = '<span>' + (icons[type] || '💡') + '</span><span>' + escapeHTML(message) + '</span>';
  container.appendChild(toast);
  setTimeout(() => {
    toast.style.opacity = '0';
    toast.style.transform = 'translateX(10px)';
    toast.style.transition = 'opacity 0.3s, transform 0.3s';
    setTimeout(() => toast.remove(), 300);
  }, 3200);
}

/* ─── INIT ───────────────────────────────── */
document.addEventListener('DOMContentLoaded', async () => {
  updRate();

  const style = document.createElement('style');
  style.textContent = `.spin{width:14px;height:14px;border:2px solid #e2e8f0;border-top-color:#6c63ff;border-radius:50%;animation:spinR 0.7s linear infinite;flex-shrink:0}@keyframes spinR{to{transform:rotate(360deg)}}`;
  document.head.appendChild(style);

  await loadCurrentUser();
  startTimer();
  loadHomeJobs();
  refreshHomeStats();
  loadSearchHistory();
  loadNotifications();
  startAutoRefresh();

  document.addEventListener('click', (e) => {
    const dd = document.getElementById('userDropdown');
    const userRow = document.querySelector('.user-row');
    if (dd && userRow && !userRow.contains(e.target) && !dd.contains(e.target)) {
      dd.style.display = 'none';
    }
  });

  document.addEventListener('keydown', (e) => {
    if (e.key === 'Escape') closeSidebar();
  });
});
