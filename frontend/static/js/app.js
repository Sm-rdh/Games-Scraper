/* ═══════════════════════════════════════════════════════════════
   app.js — games-scraper frontend logic
   Screens: quiz → loading → dashboard
   ═══════════════════════════════════════════════════════════════ */

// ── State ──────────────────────────────────────────────────────
const state = {
  questions:   [],
  currentQ:    0,
  answers:     {},          // { genre, pacing, art_style, multiplayer }
  results:     [],
};

// ── Screen helpers ─────────────────────────────────────────────
function showScreen(id) {
  document.querySelectorAll('.screen').forEach(s => s.classList.remove('active'));
  document.getElementById(id).classList.add('active');
}

// ── Init ───────────────────────────────────────────────────────
async function init() {
  try {
    const res = await fetch('/api/questions');
    const data = await res.json();
    state.questions = data.questions;
    renderQuestion(0);
    showScreen('screen-quiz');
  } catch (err) {
    console.error('Failed to load questions:', err);
  }
}

// ── Quiz rendering ─────────────────────────────────────────────
function renderQuestion(index) {
  const q = state.questions[index];
  if (!q) return;

  const total = state.questions.length;

  // Progress
  document.getElementById('progress-bar').style.width =
    `${((index + 1) / total) * 100}%`;
  document.getElementById('progress-label').textContent =
    `${index + 1} / ${total}`;
  document.getElementById('question-number').textContent =
    `QUESTION ${String(index + 1).padStart(2, '0')}`;
  document.getElementById('question-text').textContent = q.question;

  // Options
  const grid = document.getElementById('options-grid');
  grid.innerHTML = '';
  q.options.forEach(opt => {
    const btn = document.createElement('button');
    btn.className = 'option-btn';
    btn.textContent = opt.label;
    btn.dataset.value = opt.value;

    // Restore previous selection
    if (state.answers[q.id] === opt.value) {
      btn.classList.add('selected');
    }

    btn.addEventListener('click', () => selectOption(q.id, opt.value, btn));
    grid.appendChild(btn);
  });

  // Back button visibility
  document.getElementById('btn-back').style.visibility =
    index === 0 ? 'hidden' : 'visible';

  // Next button state
  updateNextBtn(q.id);

  // Animate in
  const block = document.getElementById('question-block');
  block.style.animation = 'none';
  block.offsetHeight; // reflow
  block.style.animation = 'fadeSlideUp 0.4s ease';
}

function selectOption(questionId, value, clickedBtn) {
  // Deselect all
  document.querySelectorAll('.option-btn').forEach(b =>
    b.classList.remove('selected')
  );
  // Select clicked
  clickedBtn.classList.add('selected');
  state.answers[questionId] = value;
  updateNextBtn(questionId);
}

function updateNextBtn(questionId) {
  const btn = document.getElementById('btn-next');
  const isLast = state.currentQ === state.questions.length - 1;
  btn.disabled = !state.answers[questionId];
  btn.textContent = isLast ? 'GET MY GAMES →' : 'NEXT →';
}

function quizNext() {
  const q = state.questions[state.currentQ];
  if (!state.answers[q.id]) return;

  if (state.currentQ < state.questions.length - 1) {
    state.currentQ++;
    renderQuestion(state.currentQ);
  } else {
    submitQuiz();
  }
}

function quizBack() {
  if (state.currentQ > 0) {
    state.currentQ--;
    renderQuestion(state.currentQ);
  }
}

// ── Submit quiz ────────────────────────────────────────────────
async function submitQuiz() {
  showScreen('screen-loading');

  const payload = {
    genre:       state.answers.genre,
    pacing:      state.answers.pacing,
    art_style:   state.answers.art_style,
    multiplayer: state.answers.multiplayer,
    top_n:       12,
  };

  try {
    const res  = await fetch('/api/recommend', {
      method:  'POST',
      headers: { 'Content-Type': 'application/json' },
      body:    JSON.stringify(payload),
    });
    const data = await res.json();
    state.results = data.results || [];
    renderDashboard();
    showScreen('screen-dashboard');
    loadManifestStats();
  } catch (err) {
    console.error('Recommendation failed:', err);
    alert('Something went wrong. Please try again.');
    showScreen('screen-quiz');
  }
}

// ── Dashboard ──────────────────────────────────────────────────
function renderDashboard() {
  // Hero text
  const genreLabel = capitalise(state.answers.genre || 'Game');
  document.getElementById('hero-title').textContent =
    `YOUR ${genreLabel.toUpperCase()} PICKS`;
  document.getElementById('hero-sub').textContent =
    `${state.results.length} games matched your preferences`;

  // Nav tag
  const tags = [
    state.answers.genre,
    state.answers.pacing,
    state.answers.art_style,
    state.answers.multiplayer,
  ].filter(Boolean).map(t => t.toUpperCase()).join('  ·  ');
  document.getElementById('dash-tag').textContent = tags;

  // Cards
  const grid = document.getElementById('game-grid');
  grid.innerHTML = '';

  if (!state.results.length) {
    grid.innerHTML = '<div class="no-results">NO RESULTS — TRY RETAKING THE QUIZ</div>';
    return;
  }

  state.results.forEach((game, i) => {
    grid.appendChild(buildCard(game, i));
  });
}

function buildCard(game, index) {
  const card = document.createElement('div');
  card.className = 'game-card';
  card.addEventListener('click', () => openModal(game));

  // Source badge
  const isEpic = (game.source || '').includes('epic');
  const badgeClass = isEpic ? 'badge-epic' : 'badge-steam';
  const badgeLabel = isEpic ? 'EPIC' : 'STEAM';

  // Image
  const imgSrc = game.image || '';

  card.innerHTML = `
    <span class="card-source-badge ${badgeClass}">${badgeLabel}</span>
    ${imgSrc
      ? `<img class="card-image" src="${imgSrc}" alt="${escHtml(game.name)}"
             onerror="this.parentElement.querySelector('.card-image').style.display='none'" />`
      : `<div class="img-placeholder">⬡</div>`
    }
    <div class="card-overlay"></div>
    <div class="card-content">
      <span class="card-score">${game.match_score}% MATCH</span>
      <div class="card-name">${escHtml(game.name)}</div>
      <div class="card-meta">
        ${(game.genres || []).slice(0, 2).map(g =>
          `<span class="card-tag">${g}</span>`
        ).join('')}
        <span class="card-tag">${game.price || 'FREE'}</span>
      </div>
    </div>
  `;

  // Staggered entrance animation
  card.style.opacity = '0';
  card.style.transform = 'translateY(16px)';
  setTimeout(() => {
    card.style.transition = 'opacity 0.35s ease, transform 0.35s ease';
    card.style.opacity = '1';
    card.style.transform = 'translateY(0)';
  }, index * 60);

  return card;
}

// ── Modal ──────────────────────────────────────────────────────
function openModal(game) {
  document.getElementById('modal-image').src   = game.image || '';
  document.getElementById('modal-image').alt   = game.name;
  document.getElementById('modal-score').textContent =
    `${game.match_score}% MATCH`;
  document.getElementById('modal-source').textContent =
    (game.source || '').includes('epic') ? 'EPIC GAMES' : 'STEAM';
  document.getElementById('modal-title').textContent  = game.name;
  document.getElementById('modal-desc').textContent   =
    game.description || 'No description available.';
  document.getElementById('modal-price').textContent  = game.price || 'Free';
  document.getElementById('modal-pacing').textContent = game.pacing || '—';
  document.getElementById('modal-art').textContent    = game.art_style || '—';
  document.getElementById('modal-platforms').textContent =
    (game.platforms || []).join(', ') || '—';

  // Tags
  const tagsEl = document.getElementById('modal-tags');
  const allTags = [
    ...(game.genres || []),
    game.pacing,
    game.art_style,
    ...(game.multiplayer || []),
  ].filter(Boolean);
  tagsEl.innerHTML = allTags.map(t =>
    `<span class="modal-tag">${t}</span>`
  ).join('');

  document.getElementById('modal-overlay').classList.add('open');
}

function closeModal() {
  document.getElementById('modal-overlay').classList.remove('open');
}

// ── Manage Files ───────────────────────────────────────────────
function toggleManage() {
  document.getElementById('manage-panel').classList.toggle('open');
}

async function loadManifestStats() {
  try {
    const res  = await fetch('/api/manifest');
    const data = await res.json();
    document.getElementById('stat-steam').textContent = data.steam_count ?? '—';
    document.getElementById('stat-epic').textContent  = data.epic_count  ?? '—';
    const d = data.scraped_at
      ? new Date(data.scraped_at).toLocaleDateString()
      : '—';
    document.getElementById('stat-date').textContent = d;
  } catch {
    // Manifest endpoint not critical
  }
}

async function triggerScrape() {
  const status = document.getElementById('manage-status');
  status.textContent = 'SCRAPING...';
  try {
    const res  = await fetch('/api/scrape', { method: 'POST' });
    const data = await res.json();
    status.textContent =
      `DONE — ${data.total_count} games scraped`;
    loadManifestStats();
  } catch {
    status.textContent = 'SCRAPE FAILED';
  }
}

async function reloadData() {
  const status = document.getElementById('manage-status');
  status.textContent = 'RELOADING...';
  try {
    const res  = await fetch('/api/reload', { method: 'POST' });
    const data = await res.json();
    status.textContent = `RELOADED — ${data.games_loaded} games in model`;
  } catch {
    status.textContent = 'RELOAD FAILED';
  }
}

// ── Reset ──────────────────────────────────────────────────────
function resetQuiz() {
  state.currentQ = 0;
  state.answers  = {};
  state.results  = [];
  renderQuestion(0);
  showScreen('screen-quiz');
}

// ── Utils ──────────────────────────────────────────────────────
function capitalise(str) {
  return str ? str.charAt(0).toUpperCase() + str.slice(1) : '';
}
function escHtml(str) {
  return String(str)
    .replace(/&/g,'&amp;').replace(/</g,'&lt;')
    .replace(/>/g,'&gt;').replace(/"/g,'&quot;');
}

// ── Start ──────────────────────────────────────────────────────
document.addEventListener('DOMContentLoaded', init);