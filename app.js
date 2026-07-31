// ─────────────────────────────────────────────────────────
// StudyMate frontend logic
// State (exams, subjects) is kept in-memory + localStorage
// so it survives a page refresh without needing a database.
// ─────────────────────────────────────────────────────────

const state = {
  exams: JSON.parse(localStorage.getItem('sm_exams') || '[]'),
  subjectsSeen: JSON.parse(localStorage.getItem('sm_subjects') || '[]'),
  streak: parseInt(localStorage.getItem('sm_streak') || '0', 10),
};

// ── Tiny markdown renderer (headings, bold, lists, tables) ──
function renderMarkdown(md) {
  if (!md) return '';
  let html = md
    .replace(/&/g, '&amp;').replace(/</g, '&lt;').replace(/>/g, '&gt;');

  // tables
  html = html.replace(/((?:^\|.*\|\r?\n)+)/gm, (block) => {
    const rows = block.trim().split('\n').map(r => r.trim());
    if (rows.length < 2) return block;
    const header = rows[0].split('|').filter(Boolean).map(c => c.trim());
    const bodyRows = rows.slice(2).map(r => r.split('|').filter(Boolean).map(c => c.trim()));
    let t = '<table><thead><tr>' + header.map(h => `<th>${h}</th>`).join('') + '</tr></thead><tbody>';
    bodyRows.forEach(r => { t += '<tr>' + r.map(c => `<td>${c}</td>`).join('') + '</tr>'; });
    t += '</tbody></table>';
    return t;
  });

  html = html
    .replace(/^### (.*)$/gm, '<h3>$1</h3>')
    .replace(/^## (.*)$/gm, '<h2>$1</h2>')
    .replace(/^# (.*)$/gm, '<h1>$1</h1>')
    .replace(/\*\*(.*?)\*\*/g, '<strong>$1</strong>')
    .replace(/`([^`]+)`/g, '<code>$1</code>');

  // lists
  html = html.replace(/(^|\n)((?:[-*] .*(?:\n|$))+)/g, (m, lead, block) => {
    const items = block.trim().split('\n').map(l => l.replace(/^[-*]\s?/, ''));
    return lead + '<ul>' + items.map(i => `<li>${i}</li>`).join('') + '</ul>';
  });
  html = html.replace(/(^|\n)((?:\d+\. .*(?:\n|$))+)/g, (m, lead, block) => {
    const items = block.trim().split('\n').map(l => l.replace(/^\d+\.\s?/, ''));
    return lead + '<ol>' + items.map(i => `<li>${i}</li>`).join('') + '</ol>';
  });

  // paragraphs (lines not already wrapped in a tag)
  html = html.split('\n').map(line => {
    const t = line.trim();
    if (!t) return '';
    if (/^<(h1|h2|h3|ul|ol|li|table|thead|tbody|tr|th|td)/.test(t)) return t;
    return `<p>${t}</p>`;
  }).join('\n');

  return html;
}

// ── Tabs ──────────────────────────────────────────────────
document.querySelectorAll('.tab').forEach(btn => {
  btn.addEventListener('click', () => {
    document.querySelectorAll('.tab').forEach(b => b.classList.remove('active'));
    document.querySelectorAll('.panel').forEach(p => p.classList.remove('active'));
    btn.classList.add('active');
    document.getElementById('panel-' + btn.dataset.tab).classList.add('active');
  });
});

// ── Theme toggle ──────────────────────────────────────────
const themeToggle = document.getElementById('themeToggle');
const iconSun = document.getElementById('iconSun');
const iconMoon = document.getElementById('iconMoon');
function applyTheme(theme) {
  document.documentElement.setAttribute('data-theme', theme);
  localStorage.setItem('sm_theme', theme);
  iconSun.style.display = theme === 'dark' ? 'none' : 'block';
  iconMoon.style.display = theme === 'dark' ? 'block' : 'none';
}
applyTheme(localStorage.getItem('sm_theme') || 'light');
themeToggle.addEventListener('click', () => {
  const current = document.documentElement.getAttribute('data-theme');
  applyTheme(current === 'dark' ? 'light' : 'dark');
});

// ── Health check / config banner ─────────────────────────
async function checkHealth() {
  const dot = document.getElementById('statusDot');
  const banner = document.getElementById('configBanner');
  const bannerText = document.getElementById('configBannerText');
  try {
    const res = await fetch('/api/health');
    const data = await res.json();
    if (data.configured) {
      dot.className = 'status-dot ok';
      dot.title = `Connected — model: ${data.model_primary}`;
      banner.hidden = true;
    } else {
      dot.className = 'status-dot error';
      dot.title = 'Not configured';
      bannerText.textContent = 'IBM_API_KEY or WATSONX_PROJECT_ID is missing from .env. Add them and restart the app.';
      banner.hidden = false;
    }
  } catch (e) {
    dot.className = 'status-dot error';
    banner.hidden = false;
    bannerText.textContent = 'Could not reach the backend. Is the Flask server running?';
  }
}
document.getElementById('configBannerRetry').addEventListener('click', checkHealth);
checkHealth();

// ── Today date ────────────────────────────────────────────
document.getElementById('todayDate').textContent =
  new Date().toLocaleDateString(undefined, { weekday: 'long', year: 'numeric', month: 'long', day: 'numeric' });

// ── Daily tip ─────────────────────────────────────────────
async function loadTip() {
  const el = document.getElementById('dailyTip');
  el.textContent = 'Loading a tip for you…';
  try {
    const res = await fetch('/api/tip');
    const data = await res.json();
    el.textContent = data.tip || 'Could not load a tip right now.';
  } catch {
    el.textContent = 'Could not reach the agent for a tip.';
  }
}
document.getElementById('refreshTip').addEventListener('click', loadTip);
loadTip();

// ── Exams ─────────────────────────────────────────────────
function saveExams() { localStorage.setItem('sm_exams', JSON.stringify(state.exams)); }

function renderExams() {
  const list = document.getElementById('examList');
  document.getElementById('statExams').textContent = state.exams.length;
  if (!state.exams.length) {
    list.innerHTML = '<p class="empty-state">No exams yet. Add one to start the countdown.</p>';
    return;
  }
  const today = new Date(); today.setHours(0,0,0,0);
  const withDays = state.exams.map(e => {
    const d = new Date(e.date + 'T00:00:00');
    const days = Math.round((d - today) / 86400000);
    return { ...e, days };
  }).sort((a,b) => a.days - b.days);

  list.innerHTML = withDays.map(e => `
    <div class="exam-item">
      <span class="exam-name">${e.name}</span>
      <span class="exam-days">${e.days > 0 ? e.days + 'd left' : e.days === 0 ? 'Today' : 'Past'}</span>
    </div>
  `).join('');
}
renderExams();

const examModal = document.getElementById('examModalOverlay');
document.getElementById('addExamBtn').addEventListener('click', () => { examModal.hidden = false; });
document.getElementById('examModalCancel').addEventListener('click', () => { examModal.hidden = true; });
document.getElementById('examModalSave').addEventListener('click', () => {
  const name = document.getElementById('examName').value.trim();
  const date = document.getElementById('examModalDate').value;
  if (!name || !date) return;
  state.exams.push({ name, date });
  saveExams();
  renderExams();
  document.getElementById('examName').value = '';
  document.getElementById('examModalDate').value = '';
  examModal.hidden = true;
});

// ── Pomodoro timer ────────────────────────────────────────
let pomoSeconds = 25 * 60;
let pomoRunning = false;
let pomoInterval = null;
let pomoIsBreak = false;

function formatTime(s) {
  const m = Math.floor(s / 60).toString().padStart(2, '0');
  const sec = (s % 60).toString().padStart(2, '0');
  return `${m}:${sec}`;
}
function updatePomoDisplay() {
  document.getElementById('pomoTime').textContent = formatTime(pomoSeconds);
  document.getElementById('pomoLabel').textContent = pomoIsBreak ? 'Break' : 'Focus';
}
document.getElementById('pomoStart').addEventListener('click', () => {
  const btn = document.getElementById('pomoStart');
  if (pomoRunning) {
    clearInterval(pomoInterval); pomoRunning = false; btn.textContent = 'Start';
    return;
  }
  pomoRunning = true; btn.textContent = 'Pause';
  pomoInterval = setInterval(() => {
    pomoSeconds--;
    if (pomoSeconds <= 0) {
      pomoIsBreak = !pomoIsBreak;
      pomoSeconds = pomoIsBreak ? 5 * 60 : 25 * 60;
      if (!pomoIsBreak) {
        state.streak++;
        localStorage.setItem('sm_streak', state.streak);
        document.getElementById('statStreak').textContent = state.streak;
      }
    }
    updatePomoDisplay();
  }, 1000);
});
document.getElementById('pomoReset').addEventListener('click', () => {
  clearInterval(pomoInterval); pomoRunning = false; pomoIsBreak = false;
  pomoSeconds = 25 * 60; updatePomoDisplay();
  document.getElementById('pomoStart').textContent = 'Start';
});
document.getElementById('statStreak').textContent = state.streak;
updatePomoDisplay();

// ── Planner: subject rows ────────────────────────────────
function addSubjectRow(name = '') {
  const wrap = document.getElementById('subjectRows');
  const row = document.createElement('div');
  row.className = 'subject-row';
  row.innerHTML = `
    <input type="text" class="subj-name" placeholder="Subject name" value="${name}">
    <select class="subj-difficulty">
      <option value="easy">Easy</option>
      <option value="medium" selected>Medium</option>
      <option value="hard">Hard</option>
    </select>
    <select class="subj-priority">
      <option value="normal" selected>Normal</option>
      <option value="high">High priority</option>
    </select>
    <button type="button" class="remove-row" title="Remove">✕</button>
  `;
  row.querySelector('.remove-row').addEventListener('click', () => row.remove());
  wrap.appendChild(row);
}
addSubjectRow();
document.getElementById('addSubjectRow').addEventListener('click', () => addSubjectRow());

// ── Planner: generate schedule ───────────────────────────
document.getElementById('plannerForm').addEventListener('submit', async (e) => {
  e.preventDefault();
  const btn = document.getElementById('generateBtn');
  const examDate = document.getElementById('examDate').value;
  const dailyHours = parseFloat(document.getElementById('dailyHours').value) || 4;

  const subjects = Array.from(document.querySelectorAll('.subject-row')).map(row => ({
    name: row.querySelector('.subj-name').value.trim(),
    difficulty: row.querySelector('.subj-difficulty').value,
    priority: row.querySelector('.subj-priority').value,
  })).filter(s => s.name);

  if (!examDate || !subjects.length) {
    alert('Please add an exam date and at least one subject.');
    return;
  }

  state.subjectsSeen = [...new Set([...state.subjectsSeen, ...subjects.map(s => s.name)])];
  localStorage.setItem('sm_subjects', JSON.stringify(state.subjectsSeen));
  document.getElementById('statSubjects').textContent = state.subjectsSeen.length;

  btn.disabled = true; btn.textContent = 'Generating…';
  const card = document.getElementById('scheduleResultCard');
  const out = document.getElementById('scheduleResult');
  card.hidden = false;
  out.innerHTML = '<p class="muted">Thinking through your schedule…</p>';

  try {
    const res = await fetch('/api/schedule/generate', {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ subjects, exam_date: examDate, daily_hours: dailyHours }),
    });
    const data = await res.json();
    out.innerHTML = renderMarkdown(data.schedule || data.error || 'No response received.');
  } catch (err) {
    out.innerHTML = `<p class="muted">Request failed: ${err}</p>`;
  } finally {
    btn.disabled = false; btn.textContent = 'Generate schedule';
  }
});

document.getElementById('statSubjects').textContent = state.subjectsSeen.length;

// ── Revision tracker ──────────────────────────────────────
document.getElementById('revisionForm').addEventListener('submit', async (e) => {
  e.preventDefault();
  const btn = document.getElementById('revisionBtn');
  const subject = document.getElementById('revSubject').value.trim();
  const examDate = document.getElementById('revExamDate').value;
  const topics = document.getElementById('revTopics').value.split(',').map(t => t.trim()).filter(Boolean);
  const weak = document.getElementById('revWeak').value.split(',').map(t => t.trim()).filter(Boolean);

  if (!subject || !topics.length) {
    alert('Please add a subject and at least one topic.');
    return;
  }

  btn.disabled = true; btn.textContent = 'Generating…';
  const card = document.getElementById('revisionResultCard');
  const out = document.getElementById('revisionResult');
  card.hidden = false;
  out.innerHTML = '<p class="muted">Building your revision plan…</p>';

  try {
    const res = await fetch('/api/revision/plan', {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ subject, exam_date: examDate, topics, weak_areas: weak }),
    });
    const data = await res.json();
    out.innerHTML = renderMarkdown(data.plan || data.error || 'No response received.');
  } catch (err) {
    out.innerHTML = `<p class="muted">Request failed: ${err}</p>`;
  } finally {
    btn.disabled = false; btn.textContent = 'Generate revision plan';
  }
});

// ── Chat ──────────────────────────────────────────────────
const chatMessages = document.getElementById('chatMessages');

function appendMessage(role, html) {
  const div = document.createElement('div');
  div.className = `chat-msg ${role}`;
  div.innerHTML = `<div class="bubble">${html}</div>`;
  chatMessages.appendChild(div);
  chatMessages.scrollTop = chatMessages.scrollHeight;
  return div;
}

document.getElementById('chatForm').addEventListener('submit', async (e) => {
  e.preventDefault();
  const input = document.getElementById('chatInput');
  const message = input.value.trim();
  if (!message) return;

  appendMessage('user', message.replace(/</g, '&lt;'));
  input.value = '';

  const typingEl = appendMessage('assistant', '<span class="typing-dots"><span></span><span></span><span></span></span>');

  try {
    const res = await fetch('/api/chat', {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ message }),
    });
    const data = await res.json();
    typingEl.querySelector('.bubble').innerHTML = renderMarkdown(data.reply || data.error || 'No response.');
  } catch (err) {
    typingEl.querySelector('.bubble').textContent = `Request failed: ${err}`;
  }
  chatMessages.scrollTop = chatMessages.scrollHeight;
});
