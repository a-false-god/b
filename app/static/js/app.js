/**
 * Prawko B MVP Frontend Application
 * Vanilla JS logic for Nauka, Panel Analizy (6 Analytics), and Review Queue
 */

let state = {
  view: 'dashboard',
  learningMode: 'auto', // 'auto' (Session Composer) or 'drill' (Weak Point Drill)
  user: null,
  questions: [],
  currentIndex: 0,
  currentQuestion: null,
  sessionId: 'sess_' + Math.random().toString(36).substring(2, 10),
  questionStartTime: Date.now(),
  answered: false,
  filters: {
    scope: '',
    axisA: '',
    axisB: '',
    q: ''
  },
  examState: null
};

document.addEventListener('DOMContentLoaded', () => {
  initRouter();
  initFilters();
  initHotkeys();
  initTouchSwipe();
  initServiceWorker();
  checkAuth();
  switchView('dashboard');
  loadQuestions();
});

function initServiceWorker() {
  if ('serviceWorker' in navigator) {
    navigator.serviceWorker.register('/static/sw.js').catch(err => {
      console.warn("ServiceWorker registration failed:", err);
    });
  }
}

function initTouchSwipe() {
  let touchStartX = 0;
  let touchStartY = 0;

  document.addEventListener('touchstart', (e) => {
    touchStartX = e.changedTouches[0].screenX;
    touchStartY = e.changedTouches[0].screenY;
  }, { passive: true });

  document.addEventListener('touchend', (e) => {
    const touchEndX = e.changedTouches[0].screenX;
    const touchEndY = e.changedTouches[0].screenY;
    const diffX = touchEndX - touchStartX;
    const diffY = touchEndY - touchStartY;

    // Horizontal swipe threshold: > 60px horizontal, < 40px vertical
    if (Math.abs(diffX) > 60 && Math.abs(diffY) < 40) {
      if (diffX < 0) {
        navigateNext();
      } else {
        navigatePrev();
      }
    }
  }, { passive: true });
}

function initRouter() {
  document.querySelectorAll('nav a').forEach(link => {
    link.addEventListener('click', (e) => {
      e.preventDefault();
      const view = e.target.getAttribute('data-view');
      switchView(view);
    });
  });
}

function switchView(viewName) {
  state.view = viewName;
  document.querySelectorAll('nav a').forEach(a => {
    a.classList.toggle('active', a.getAttribute('data-view') === viewName);
  });

  document.getElementById('view-dashboard').style.display = viewName === 'dashboard' ? 'block' : 'none';
  document.getElementById('view-nauka').style.display = viewName === 'nauka' ? 'block' : 'none';
  document.getElementById('view-analiza').style.display = viewName === 'analiza' ? 'block' : 'none';
  document.getElementById('view-review').style.display = viewName === 'review' ? 'block' : 'none';

  if (viewName === 'dashboard') loadDashboard();
  if (viewName === 'analiza') loadAnalytics();
  if (viewName === 'review') loadReviewQueue();
}

function checkAuth() {
  const savedUser = localStorage.getItem('prawko_user');
  if (savedUser) {
    state.user = JSON.parse(savedUser);
  }
  renderAuthStatus();
}

function renderAuthStatus() {
  const bar = document.getElementById('auth-status');
  if (!bar) return;

  if (state.user) {
    bar.innerHTML = `
      <span style="font-size: 0.9rem; color: var(--text-muted);">👤 <strong>${state.user.login}</strong></span>
      <button class="btn-secondary" style="padding: 0.3rem 0.6rem; font-size: 0.8rem;" onclick="handleLogout()">Wyloguj</button>
    `;
  } else {
    bar.innerHTML = `
      <button class="btn-secondary" style="padding: 0.35rem 0.75rem; font-size: 0.85rem;" onclick="openAuthModal()">🔑 Zaloguj / Rejestracja</button>
    `;
  }
}

function openAuthModal(msg) {
  const modal = document.getElementById('auth-modal');
  const errDiv = document.getElementById('auth-error-msg');
  if (errDiv) errDiv.innerText = msg || '';
  if (modal) modal.style.display = 'flex';
}

function closeAuthModal() {
  const modal = document.getElementById('auth-modal');
  if (modal) modal.style.display = 'none';
}

async function handleAuthSubmit(mode) {
  const loginInput = document.getElementById('auth-login');
  const passwordInput = document.getElementById('auth-password');
  const errDiv = document.getElementById('auth-error-msg');

  const login = loginInput ? loginInput.value.trim() : '';
  const password = passwordInput ? passwordInput.value : '';

  if (!login || !password) {
    if (errDiv) errDiv.innerText = 'Podaj login i hasło.';
    return;
  }

  const endpoint = mode === 'register' ? '/auth/register' : '/auth/login';

  try {
    const res = await fetch(endpoint, {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ login, password })
    });

    if (!res.ok) {
      const errData = await res.json();
      if (errDiv) errDiv.innerText = errData.detail || 'Błąd autoryzacji.';
      return;
    }

    const userData = await res.json();
    state.user = userData;
    localStorage.setItem('prawko_user', JSON.stringify(userData));
    renderAuthStatus();
    closeAuthModal();

    if (state.view === 'analiza') loadAnalytics();
  } catch (err) {
    if (errDiv) errDiv.innerText = 'Błąd połączenia z serwerem.';
  }
}

async function handleLogout() {
  try {
    await fetch('/auth/logout', { method: 'POST' });
  } catch (e) {}

  state.user = null;
  localStorage.removeItem('prawko_user');
  renderAuthStatus();
  if (state.view === 'analiza') loadAnalytics();
}

function initFilters() {
  const scopeSelect = document.getElementById('filter-scope');
  const axisASelect = document.getElementById('filter-axisA');
  const axisBSelect = document.getElementById('filter-axisB');
  const searchInput = document.getElementById('filter-search');

  let debounceTimer;
  const triggerLoad = () => {
    clearTimeout(debounceTimer);
    debounceTimer = setTimeout(() => {
      loadQuestions();
    }, 300);
  };

  if (scopeSelect) scopeSelect.addEventListener('change', (e) => { state.filters.scope = e.target.value; loadQuestions(); });
  if (axisASelect) axisASelect.addEventListener('change', (e) => { state.filters.axisA = e.target.value; loadQuestions(); });
  if (axisBSelect) axisBSelect.addEventListener('change', (e) => { state.filters.axisB = e.target.value; loadQuestions(); });
  if (searchInput) searchInput.addEventListener('input', (e) => { state.filters.q = e.target.value; triggerLoad(); });
}

function switchLearningMode(mode) {
  state.learningMode = mode;
  const autoBtn = document.getElementById('btn-mode-auto');
  const drillBtn = document.getElementById('btn-mode-drill');
  const filterBar = document.getElementById('learning-filter-bar');
  const titleText = document.getElementById('mode-title-text');
  const descText = document.getElementById('mode-desc-text');

  if (autoBtn) autoBtn.classList.toggle('active', mode === 'auto');
  if (drillBtn) drillBtn.classList.toggle('active', mode === 'drill');

  if (mode === 'auto') {
    if (filterBar) filterBar.style.display = 'none';
    if (titleText) titleText.innerText = '⚡ Kompozytor Sesji (Domyślny)';
    if (descText) descText.innerText = 'Kolejka priorytetowa (niewidziane 3-pkt → błędy → powtórki) z przeplataniem domen';
  } else {
    if (filterBar) filterBar.style.display = 'flex';
    if (titleText) titleText.innerText = '🎯 Tryb Słaby Punkt';
    if (descText) descText.innerText = 'Wybierz filtry dziedzinowe i szukaj pytań pod konkretny temat';
  }

  loadQuestions();
}

async function loadQuestions() {
  if (state.learningMode === 'auto' && !state.filters.q && !state.filters.scope && !state.filters.axisA && !state.filters.axisB) {
    try {
      const res = await fetch('/api/session/next?mode=auto&limit=20');
      state.questions = await res.json();
      state.currentIndex = 0;
      renderCurrentQuestion();
      return;
    } catch (err) {
      console.error("Failed to load session queue, falling back to catalog:", err);
    }
  }

  const params = new URLSearchParams({
    category: 'B',
    limit: 100
  });

  if (state.filters.scope) params.append('scope', state.filters.scope);
  if (state.filters.axisA) params.append('axisA', state.filters.axisA);
  if (state.filters.axisB) params.append('axisB', state.filters.axisB);
  if (state.filters.q) params.append('q', state.filters.q);

  try {
    const res = await fetch(`/api/questions?${params.toString()}`);
    state.questions = await res.json();
    state.currentIndex = 0;
    renderCurrentQuestion();
  } catch (err) {
    console.error("Failed to load questions:", err);
  }
}

function renderCurrentQuestion() {
  const container = document.getElementById('question-container');
  if (!state.questions || state.questions.length === 0) {
    container.innerHTML = `
      <div class="question-card">
        <div class="card-body" style="text-align: center; padding: 3rem;">
          <p style="color: var(--text-muted); font-size: 1.1rem;">Brak pytań spełniających kryteria wyszukiwania.</p>
        </div>
      </div>
    `;
    return;
  }

  const q = state.questions[state.currentIndex];
  state.currentQuestion = q;
  state.questionStartTime = Date.now();
  state.answered = false;

  const mediaHtml = renderMedia(q);
  const answersHtml = renderAnswers(q);

  const is3Pt = q.points === 3;

  container.innerHTML = `
    <div class="question-card">
      <div class="media-container">${mediaHtml}</div>
      <div class="card-body">
        <div class="meta-pills">
          <span class="pill b-cat">Kat. B</span>
          <span class="pill">${q.scope}</span>
          <span class="pill points-pill ${is3Pt ? 'priority-3pt' : ''}">${q.points} PKT</span>
          ${state.learningMode === 'auto' ? '<span class="pill priority-interleaved">🔀 Przeplatana Sesja</span>' : ''}
          ${q.axis_a ? `<span class="pill axis-pill">Oś A: ${q.axis_a}</span>` : ''}
          ${q.axis_b ? `<span class="pill axis-pill">Oś B: ${q.axis_b}</span>` : ''}
          <span class="pill">Pytanie ${state.currentIndex + 1} z ${state.questions.length} (ID: ${q.id})</span>
        </div>
        <div class="question-text">${q.q_pl}</div>
        <div class="answers-grid" id="answers-grid">${answersHtml}</div>
        <div id="feedback-message" style="margin-top: 1rem;"></div>
      </div>
    </div>
  `;
}

function renderMedia(q) {
  if (!q.media) return '<div class="media-fallback">📷 Pytanie bez pliku multimedialnego</div>';

  const mediaUrl = `/media/${q.media}`;
  if (q.media_kind === 'video' || q.media.endsWith('.mp4') || q.media.endsWith('.wmv')) {
    return `<video src="${mediaUrl}" playsinline autoplay muted loop preload="auto" disablepictureinpicture class="no-controls" onerror="this.outerHTML='<div class=\\'media-fallback\\'>🎬 Plik wideo: ${q.media} (brak w katalogu media/)</div>'"></video>`;
  } else {
    return `<img src="${mediaUrl}" alt="Media do pytania" loading="lazy" onerror="this.outerHTML='<div class=\\'media-fallback\\'>🖼️ Plik graficzny: ${q.media} (brak w katalogu media/)</div>'" />`;
  }
}

function renderAnswers(q) {
  if (q.type === 'TN') {
    return `
      <button class="answer-btn" onclick="submitChoice('T')"><kbd>T</kbd> TAK</button>
      <button class="answer-btn" onclick="submitChoice('N')"><kbd>N</kbd> NIE</button>
    `;
  } else {
    return `
      <button class="answer-btn" onclick="submitChoice('A')"><kbd>A</kbd> A: ${q.a_pl || ''}</button>
      <button class="answer-btn" onclick="submitChoice('B')"><kbd>B</kbd> B: ${q.b_pl || ''}</button>
      <button class="answer-btn" onclick="submitChoice('C')"><kbd>C</kbd> C: ${q.c_pl || ''}</button>
    `;
  }
}

async function submitChoice(chosen) {
  if (state.answered || !state.currentQuestion) return;

  if (!state.user) {
    openAuthModal('Musisz się zalogować, aby zapisywać odpowiedzi i budować analitykę.');
    return;
  }

  state.answered = true;
  const elapsedMs = Date.now() - state.questionStartTime;
  const q = state.currentQuestion;

  try {
    const res = await fetch('/api/answers', {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({
        question_id: q.id,
        chosen: chosen,
        time_ms: elapsedMs,
        session_id: state.sessionId
      })
    });

    if (res.status === 401) {
      state.answered = false;
      openAuthModal('Sesja wygasła. Zaloguj się ponownie.');
      return;
    }

    const result = await res.json();
    highlightAnswerButtons(chosen, result.correct_answer, result.is_correct, result.explanation, result.legal_basis, result.pending_explanation, q.id);
  } catch (err) {
    console.error("Failed to submit answer:", err);
  }
}

function highlightAnswerButtons(chosen, correct, isCorrect, explanation, legalBasis, pendingExplanation, questionId) {
  const btns = document.querySelectorAll('.answer-btn');
  btns.forEach(btn => {
    const btnKey = btn.querySelector('kbd').innerText;
    if (btnKey === correct) {
      btn.classList.add('correct');
    } else if (btnKey === chosen && !isCorrect) {
      btn.classList.add('incorrect');
    }
  });

  const fb = document.getElementById('feedback-message');
  if (fb) {
    let expCard = '';
    if (explanation) {
      expCard = `
        <div class="elaborated-feedback-card">
          <div class="elaborated-feedback-title">
            <span>💡 Objaśnienie edukacyjne</span>
          </div>
          <div class="elaborated-feedback-text">${explanation}</div>
          ${legalBasis ? `
            <div class="legal-basis-box">
              <div class="legal-basis-title">⚖️ Podstawa Prawna:</div>
              <div>${legalBasis}</div>
            </div>
          ` : ''}
        </div>
      `;
    } else {
      expCard = '<div id="async-explanation-container"></div>';
    }

    fb.innerHTML = (isCorrect
      ? '<span style="color: var(--success); font-weight: bold;">✓ Poprawna odpowiedź!</span>'
      : `<span style="color: var(--danger); font-weight: bold;">✗ Błędna odpowiedź! Poprawna odpowiedź to: <strong>${correct}</strong></span>`) + expCard;

    if (pendingExplanation || !explanation) {
      pollExplanation(questionId);
    }
  }
}

async function pollExplanation(questionId) {
  const container = document.getElementById('async-explanation-container');
  if (!container) return;

  container.innerHTML = '<div class="legal-basis-box" style="margin-top:0.75rem; color: var(--text-muted);">⏳ Generowanie objaśnienia i podstawy prawnej w tle...</div>';

  for (let attempt = 0; attempt < 6; attempt++) {
    await new Promise(r => setTimeout(r, 500));
    try {
      const res = await fetch(`/api/questions/${questionId}/explanation`);
      if (res.ok) {
        const data = await res.json();
        if (!data.pending && data.explanation) {
          container.innerHTML = `
            <div class="elaborated-feedback-card">
              <div class="elaborated-feedback-title">
                <span>💡 Objaśnienie edukacyjne</span>
              </div>
              <div class="elaborated-feedback-text">${data.explanation}</div>
              ${data.legal_basis ? `
                <div class="legal-basis-box">
                  <div class="legal-basis-title">⚖️ Podstawa Prawna:</div>
                  <div>${data.legal_basis}</div>
                </div>
              ` : ''}
            </div>
          `;
          return;
        }
      }
    } catch (e) {}
  }
}

function navigatePrev() {
  if (state.currentIndex > 0) {
    state.currentIndex--;
    renderCurrentQuestion();
  }
}

function navigateNext() {
  if (state.currentIndex < state.questions.length - 1) {
    state.currentIndex++;
    renderCurrentQuestion();
  }
}

function initHotkeys() {
  document.addEventListener('keydown', (e) => {
    if (e.target.tagName === 'INPUT' || e.target.tagName === 'SELECT') return;

    if (state.view === 'nauka') {
      const key = e.key.toUpperCase();
      if (key === 'ARROWLEFT') {
        navigatePrev();
      } else if (key === 'ARROWRIGHT') {
        navigateNext();
      } else if (['T', 'N', 'A', 'B', 'C'].includes(key)) {
        submitChoice(key);
      }
    } else if (state.view === 'review') {
      if (e.key === '1') {
        const acceptBtn = document.getElementById('accept-review-btn');
        if (acceptBtn) acceptBtn.click();
      }
    }
  });
}

// ---------------------------------------------------------------------------
// Panel Analizy View (6 Metrics)
// ---------------------------------------------------------------------------

async function loadAnalytics() {
  const container = document.getElementById('view-analiza');
  
  if (!state.user) {
    container.innerHTML = `
      <h2>Panel Analizy Błędów</h2>
      <div class="question-card" style="margin-top: 1rem; text-align: center; padding: 3rem;">
        <p style="color: var(--text-muted); font-size: 1.1rem; margin-bottom: 1rem;">Zaloguj się, aby zobaczyć swoje statystyki błędów i wahań.</p>
        <button class="answer-btn correct" style="max-width: 240px; margin: 0 auto;" onclick="openAuthModal()">🔑 Zaloguj się</button>
      </div>
    `;
    return;
  }

  container.innerHTML = '<div style="text-align:center; padding: 2rem; color: var(--text-muted);">Ładowanie statystyk analitycznych...</div>';

  try {
    const [hardestRes, reasonRes, coverageRes, hesitationRes, axisARes, optionRes] = await Promise.all([
      fetch('/api/analytics/errors?by=question').then(r => r.status === 401 ? null : r.json()),
      fetch('/api/analytics/reason').then(r => r.status === 401 ? null : r.json()),
      fetch('/api/analytics/coverage').then(r => r.status === 401 ? null : r.json()),
      fetch('/api/analytics/hesitation').then(r => r.status === 401 ? null : r.json()),
      fetch('/api/analytics/errors?by=axisA').then(r => r.status === 401 ? null : r.json()),
      fetch('/api/analytics/errors?by=option').then(r => r.status === 401 ? null : r.json())
    ]);

    if (!reasonRes) {
      openAuthModal('Sesja wygasła. Zaloguj się ponownie.');
      return;
    }

    renderAnalyticsDashboard({
      hardest: hardestRes ? (hardestRes.data || []) : [],
      reason: reasonRes,
      coverage: coverageRes,
      hesitation: hesitationRes ? (hesitationRes.hesitation_candidates || []) : [],
      axisA: axisARes ? (axisARes.data || []) : [],
      options: optionRes ? (optionRes.data || []) : []
    });
  } catch (e) {
    console.error("Failed to load analytics dashboard", e);
    container.innerHTML = '<div style="color: var(--danger); padding: 2rem;">Błąd podczas ładowania panelu analizy.</div>';
  }
}

function renderAnalyticsDashboard(data) {
  const container = document.getElementById('view-analiza');
  const cov = data.coverage || { total_cat_b: 1, mastered: 0, seen: 0, never_seen: 1 };
  const total = cov.total_cat_b || 1;

  const pctMastered = Math.round((cov.mastered / total) * 100);
  const pctSeen = Math.round((cov.seen / total) * 100);
  const pctNever = Math.max(0, 100 - pctSeen);

  container.innerHTML = `
    <h2 style="margin-bottom: 0.5rem;">Panel Analizy Błędów (6 Wskaźników)</h2>
    <p style="color: var(--text-muted); margin-bottom: 1.5rem;">Analiza indywidualna dla użytkownika: <strong>${state.user ? state.user.login : ''}</strong></p>

    <div class="analytics-grid">
      <!-- 1. Coverage Split -->
      <div class="analytics-card">
        <h3>📊 Pokrycie Bazy Pytań (Coverage)</h3>
        <p style="font-size: 0.9rem; color: var(--text-muted);">Przerobione vs Opanowane (ostatnie 2 trafione)</p>
        <div class="coverage-bar-container">
          <div class="coverage-bar-segment mastered" style="width: ${pctMastered}%;" title="Opanowane: ${cov.mastered}"></div>
          <div class="coverage-bar-segment seen" style="width: ${pctSeen - pctMastered}%;" title="W trakcie: ${cov.seen - cov.mastered}"></div>
          <div class="coverage-bar-segment never" style="width: ${pctNever}%;" title="Niewidziane: ${cov.never_seen}"></div>
        </div>
        <div style="display: flex; justify-content: space-between; font-size: 0.85rem; color: var(--text-muted);">
          <span>🟢 Opanowane: <strong>${cov.mastered}</strong></span>
          <span>🔵 Widziane: <strong>${cov.seen}</strong></span>
          <span>⚪ Niewidziane: <strong>${cov.never_seen}</strong></span>
        </div>
      </div>

      <!-- 2. Reason Split -->
      <div class="analytics-card">
        <h3>🧠 Typologia Pomyłek (Reason Split)</h3>
        <div class="reason-stats">
          <div class="reason-item slip">
            <span>⚡ <strong>Slips</strong> (Pośpiech &lt;8s)</span>
            <strong>${data.reason.slips}</strong>
          </div>
          <div class="reason-item mistake">
            <span>🤔 <strong>Mistakes</strong> (Błąd reguły &ge;8s)</span>
            <strong>${data.reason.mistakes}</strong>
          </div>
          <div class="reason-item uncertainty">
            <span>❓ <strong>Uncertainty</strong> (Niewiedza &gt;15s)</span>
            <strong>${data.reason.uncertainty}</strong>
          </div>
        </div>
      </div>

      <!-- 3. Errors per Axis A -->
      <div class="analytics-card">
        <h3>🎯 Błędy wg Osi Poznawczej (Axis A)</h3>
        <table class="list-table">
          <thead><tr><th>Typ poznawczy</th><th>Błędy</th></tr></thead>
          <tbody>
            ${data.axisA.length ? data.axisA.map(row => `<tr><td>${row.axis_value}</td><td><strong>${row.error_count}</strong></td></tr>`).join('') : '<tr><td colspan="2">Brak zarejestrowanych błędów.</td></tr>'}
          </tbody>
        </table>
      </div>

      <!-- 4. Confused Options -->
      <div class="analytics-card">
        <h3>🔀 Mylone Opcje (ABC)</h3>
        <table class="list-table">
          <thead><tr><th>ID</th><th>Wybrana</th><th>Poprawna</th><th>Liczba</th></tr></thead>
          <tbody>
            ${data.options.slice(0, 5).map(row => `<tr><td>#${row.question_id}</td><td><span style="color:var(--danger)">${row.chosen}</span></td><td><span style="color:var(--success)">${row.correct_option}</span></td><td>${row.confused_count}</td></tr>`).join('') || '<tr><td colspan="4">Brak mylonych opcji.</td></tr>'}
          </tbody>
        </table>
      </div>

      <!-- 5. Hesitation Candidates -->
      <div class="analytics-card" style="grid-column: span 1;">
        <h3>⏱️ Wahania / Hesitation (&gt;15s)</h3>
        <ul style="padding-left: 1.2rem; font-size: 0.9rem;">
          ${data.hesitation.slice(0, 5).map(h => `<li>Pytanie #${h.question_id}: ${h.time_ms / 1000}s (${h.q_pl.substring(0, 35)}...)</li>`).join('') || '<p style="color:var(--text-muted); font-size:0.9rem;">Brak pytań z wysokim mego czasem odpowiedzi.</p>'}
        </ul>
      </div>

      <!-- 6. Hardest Questions -->
      <div class="analytics-card" style="grid-column: span 1;">
        <h3>🔥 Najtrudniejsze Pytania (Hardest)</h3>
        <ol style="padding-left: 1.2rem; font-size: 0.9rem;">
          ${data.hardest.slice(0, 5).map(q => `<li>Pytanie #${q.question_id} — <strong>${q.error_count} błędów</strong><br><span style="color:var(--text-muted)">${q.q_pl.substring(0, 45)}...</span></li>`).join('') || '<p style="color:var(--text-muted); font-size:0.9rem;">Brak błędnych pytań.</p>'}
        </ol>
      </div>
    </div>
  `;
}

// ---------------------------------------------------------------------------
// Review Queue View
// ---------------------------------------------------------------------------

async function loadReviewQueue() {
  const container = document.getElementById('view-review');
  container.innerHTML = '<div style="text-align:center; padding: 2rem; color: var(--text-muted);">Ładowanie kolejki weryfikacji...</div>';

  try {
    const res = await fetch('/api/classification/review');
    const queue = await res.json();
    renderReviewQueue(queue);
  } catch (e) {
    console.error("Failed to load review queue", e);
    container.innerHTML = '<div style="color: var(--danger); padding: 2rem;">Błąd podczas ładowania kolejki weryfikacji.</div>';
  }
}

function renderReviewQueue(queue) {
  const container = document.getElementById('view-review');
  if (!queue || queue.length === 0) {
    container.innerHTML = `
      <h2>Kolejka Weryfikacji Taksonomii</h2>
      <div class="question-card" style="margin-top: 1rem; text-align: center; padding: 2.5rem;">
        <p style="color: var(--success); font-weight: 600;">✓ Brak pytań wymagających ręcznej weryfikacji w kolejce!</p>
      </div>
    `;
    return;
  }

  const q = queue[0];
  container.innerHTML = `
    <h2>Kolejka Weryfikacji Taksonomii (Ręczna)</h2>
    <p style="color: var(--text-muted); margin-bottom: 1.5rem;">Pytania z pewnością klasyfikacji &lt;0.8 lub z plikiem multimedialnym.</p>

    <div class="question-card">
      <div class="card-body">
        <div class="meta-pills">
          <span class="pill b-cat">Kat. B</span>
          <span class="pill">Pytanie ID: ${q.id}</span>
          <span class="pill">${q.type}</span>
        </div>
        <div class="question-text">${q.q_pl}</div>
        
        <div class="review-triage-box">
          <div>
            <strong>Sugerowana Oś A (Poznawcza):</strong> ${q.sugg_a || 'brak'} (Pewność: ${q.conf_a || 0})
          </div>
          <div>
            <strong>Sugerowana Oś B (Domena):</strong> ${q.sugg_b || 'brak'} (Pewność: ${q.conf_b || 0})
          </div>

          <div class="review-actions">
            <button id="accept-review-btn" class="answer-btn correct" style="flex:1" onclick="acceptReview(${q.id}, '${q.sugg_a || 'pamiec'}', '${q.sugg_b || 'znaki_i_sygnaly'}')">
              <kbd>1</kbd> Akceptuj Sugestię
            </button>
          </div>
        </div>
      </div>
    </div>
  `;
}

async function acceptReview(questionId, axisA, axisB) {
  try {
    await fetch(`/api/classification/${questionId}`, {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({
        axis_a: axisA,
        axis_b: axisB,
        axis_c: ['brak_pulapki'],
        action: 'accept'
      })
    });
    loadReviewQueue();
  } catch (e) {
    console.error("Failed to accept classification review", e);
  }
}


// ---------------------------------------------------------------------------
// Dashboard View & Elo Ratings System
// ---------------------------------------------------------------------------

async function loadDashboard() {
  const container = document.getElementById('view-dashboard');
  if (!container) return;

  container.innerHTML = '<div style="text-align:center; padding: 3rem; color: var(--text-muted);">Ładowanie Pulpitu...</div>';

  try {
    const res = await fetch('/api/dashboard');
    if (res.ok) {
      const data = await res.json();
      renderDashboard(data);
      return;
    }
  } catch (e) {
    console.log("Using fallback/sample dashboard data");
  }

  // Fallback sample data with M6.1 structure
  const sampleData = {
    user: {
      id: 1,
      login: state.user ? state.user.login : "Jan Kowalski",
      skill_theta: 0.245,
      n: 42
    },
    skill_theta: 0.245,
    per_axis_b: {
      "znaki_i_sygnaly": 0.45,
      "pierwszenstwo": -0.12,
      "manewry_i_pozycja": 0.30
    },
    metrics: {
      total_answers: 42,
      correct_answers: 32,
      accuracy_percent: 76.2,
      mastered_count: 14,
      avg_time_ms: 6420
    },
    coverage: {
      total_cat_b: 2135,
      never_seen: 2093,
      seen: 42,
      mastered: 14
    },
    domain_performance: [
      { axis_b: "pierwszenstwo", theta: -0.12, error_count: 5, total_attempts: 12, accuracy_pct: 58.3 },
      { axis_b: "znaki_i_sygnaly", theta: 0.45, error_count: 3, total_attempts: 14, accuracy_pct: 78.6 },
      { axis_b: "manewry_i_pozycja", theta: 0.30, error_count: 2, total_attempts: 10, accuracy_pct: 80.0 },
      { axis_b: "predkosc_i_odleglosci", theta: 0.10, error_count: 0, total_attempts: 6, accuracy_pct: 100.0 }
    ],
    repeats_due: 7,
    reason_split: {
      slips: 4,
      mistakes: 5,
      uncertainty: 3
    },
    skill_history: [
      { id: 1, theta: 0.0 },
      { id: 2, theta: 0.15 },
      { id: 3, theta: 0.08 },
      { id: 4, theta: 0.21 },
      { id: 5, theta: 0.245 }
    ],
    hardest_questions: [
      { id: 412, q_pl: "Czy w tej sytuacji masz pierwszeństwo przejazdu przed pojazdem szynowym?", scope: "PODSTAWOWY", attempts: 18, wrong: 14, error_pct: 72.7, b_q: 0.98 },
      { id: 1893, q_pl: "Jaki jest dopuszczalny nacisk osi pojazdu na drogę publiczną?", scope: "SPECJALISTYCZNY", attempts: 15, wrong: 10, error_pct: 63.2, b_q: 0.54 },
      { id: 245, q_pl: "Czy w przedstawionym przypadku wolno Ci wyprzedzić pojazd z prawej strony?", scope: "PODSTAWOWY", attempts: 12, wrong: 7, error_pct: 56.3, b_q: 0.25 },
      { id: 981, q_pl: "Jaka jest maksymalna dopuszczalna prędkość samochodu osobowego na drodze ekspresowej dwujezdniowej?", scope: "SPECJALISTYCZNY", attempts: 10, wrong: 5, error_pct: 50.0, b_q: 0.00 }
    ],
    recent_activity: [
      { id: 42, question_id: 412, q_pl: "Czy w tej sytuacji masz pierwszeństwo przejazdu przed pojazdem szynowym?", chosen: "T", is_correct: 1, time_ms: 4800, created_at: "2026-08-09 17:00" },
      { id: 41, question_id: 245, q_pl: "Czy w przedstawionym przypadku wolno Ci wyprzedzić pojazd z prawej strony?", chosen: "N", is_correct: 1, time_ms: 6100, created_at: "2026-08-09 16:55" },
      { id: 40, question_id: 1893, q_pl: "Jaki jest dopuszczalny nacisk osi pojazdu...", chosen: "A", is_correct: 0, time_ms: 9200, created_at: "2026-08-09 16:50" }
    ]
  };

  renderDashboard(sampleData);
}

function renderDashboard(data) {
  const container = document.getElementById('view-dashboard');
  if (!container) return;

  const u = data.user || {};
  const m = data.metrics || {};
  const cov = data.coverage || { total_cat_b: 2135, never_seen: 2093, seen: 42, mastered: 14 };
  const reasons = data.reason_split || { slips: 0, mistakes: 0, uncertainty: 0 };
  const repeatsDue = data.repeats_due || 0;
  const globalTheta = (data.skill_theta !== undefined ? data.skill_theta : u.skill_theta) || 0.0;

  const pctMastered = Math.round((cov.mastered / (cov.total_cat_b || 1)) * 100);
  const pctSeen = Math.round((cov.seen / (cov.total_cat_b || 1)) * 100);
  const pctNever = Math.max(0, 100 - pctSeen);

  const history = data.skill_history || [];
  const minTheta = history.length > 0 ? Math.min(...history.map(h => h.theta)) : -0.5;
  const maxTheta = history.length > 0 ? Math.max(...history.map(h => h.theta)) : 0.5;
  const range = (maxTheta - minTheta) || 1.0;

  const trajectoryHtml = history.map(h => {
    const heightPct = Math.max(12, Math.min(100, (((h.theta - minTheta) / range) * 88) + 12));
    return `<div class="trajectory-bar" style="height: ${heightPct}%;" title="θ = ${h.theta.toFixed(3)}"></div>`;
  }).join('');

  container.innerHTML = `
    <!-- Header Banner -->
    <div class="dashboard-header-card">
      <div>
        <h1 style="font-size: 1.6rem; font-weight: 700; margin-bottom: 0.25rem;">Witaj, ${u.login || 'Użytkowniku'}!</h1>
        <p style="color: var(--text-muted); font-size: 0.9rem;">Model asymetryczny Rascha — wskaźnik umiejętności (θ) i statystyka empirią błędów pytania.</p>
      </div>
      <div style="text-align: right;">
        <div class="theta-badge">
          <span>Umiejętność Użytkownika</span>
        </div>
        <div style="font-size: 2rem; font-weight: 700; margin-top: 0.3rem; color: var(--text-main);">
          θ = ${globalTheta >= 0 ? '+' : ''}${typeof globalTheta === 'number' ? globalTheta.toFixed(3) : globalTheta}
        </div>
      </div>
    </div>

    <!-- 1. Stat Metrics Grid -->
    <div class="dashboard-stats-grid">
      <div class="dashboard-metric-card">
        <span class="metric-label">Umiejętność (θ)</span>
        <span class="metric-value">${globalTheta >= 0 ? '+' : ''}${typeof globalTheta === 'number' ? globalTheta.toFixed(3) : globalTheta}</span>
        <span style="font-size: 0.8rem; color: var(--text-muted); margin-top: 0.3rem;">Prób (n): ${u.n || m.total_answers || 0}</span>
      </div>

      <div class="dashboard-metric-card">
        <span class="metric-label">Skuteczność</span>
        <span class="metric-value">${m.accuracy_percent || 0}%</span>
        <span style="font-size: 0.8rem; color: var(--text-muted); margin-top: 0.3rem;">${m.correct_answers || 0} z ${m.total_answers || 0} poprawnych</span>
      </div>

      <div class="dashboard-metric-card">
        <span class="metric-label">Opanowane Pytania</span>
        <span class="metric-value">${m.mastered_count || 0}</span>
        <span style="font-size: 0.8rem; color: var(--text-muted); margin-top: 0.3rem;">2 ostatnie trafienia z rzędu</span>
      </div>

      <div class="dashboard-metric-card">
        <span class="metric-label">Powtórki Dziś</span>
        <span class="metric-value" style="color: var(--danger)">${repeatsDue}</span>
        <button class="btn-secondary" style="margin-top: 0.5rem; padding: 0.3rem 0.6rem; font-size: 0.8rem;" onclick="switchView('nauka')">Rozpocznij powtórkę</button>
      </div>
    </div>

    <!-- 2. Coverage & Reason Split Section -->
    <div style="display: grid; grid-template-columns: 1fr 1fr; gap: 1.25rem; margin-bottom: 1.25rem;">
      <div class="analytics-card">
        <h3>📊 Pokrycie Bazy Pytań (Never / Seen / Mastered)</h3>
        <p style="font-size: 0.825rem; color: var(--text-muted); margin-bottom: 0.85rem;">Postęp przerabiania pytań kategorii B</p>
        <div class="coverage-bar-container">
          <div class="coverage-bar-segment mastered" style="width: ${pctMastered}%;" title="Opanowane: ${cov.mastered}"></div>
          <div class="coverage-bar-segment seen" style="width: ${pctSeen - pctMastered}%;" title="W trakcie: ${cov.seen - cov.mastered}"></div>
          <div class="coverage-bar-segment never" style="width: ${pctNever}%;" title="Niewidziane: ${cov.never_seen}"></div>
        </div>
        <div style="display: flex; justify-content: space-between; font-size: 0.825rem; color: var(--text-muted);">
          <span>🟢 Opanowane: <strong>${cov.mastered}</strong></span>
          <span>🔵 Widziane: <strong>${cov.seen}</strong></span>
          <span>⚪ Niewidziane: <strong>${cov.never_seen}</strong></span>
        </div>
      </div>

      <div class="analytics-card">
        <h3>🧠 Typologia Błędów (Reason Split)</h3>
        <p style="font-size: 0.825rem; color: var(--text-muted); margin-bottom: 0.85rem;">Klasyfikacja według czasu reakcji</p>
        <div class="reason-stats">
          <div class="reason-item slip">
            <span>⚡ <strong>Slips</strong> (&lt;8s)</span>
            <strong>${reasons.slips}</strong>
          </div>
          <div class="reason-item mistake">
            <span>🤔 <strong>Mistakes</strong> (&ge;8s)</span>
            <strong>${reasons.mistakes}</strong>
          </div>
          <div class="reason-item uncertainty">
            <span>❓ <strong>Uncertainty</strong> (&gt;15s)</span>
            <strong>${reasons.uncertainty}</strong>
          </div>
        </div>
      </div>
    </div>

    <!-- 3. Trajectory & Domain Performance Grid -->
    <div style="display: grid; grid-template-columns: 1fr 1fr; gap: 1.25rem; margin-bottom: 1.25rem;">
      <div class="analytics-card">
        <h3>📈 Trajektoria Umiejętności (θ Sparkline)</h3>
        <p style="font-size: 0.825rem; color: var(--text-muted); margin-bottom: 0.85rem;">Ewolucja poziomu θ z każdym rozwiązany pytaniem</p>
        <div class="trajectory-chart">
          ${trajectoryHtml || '<div style="color: var(--text-muted); font-size: 0.85rem;">Brak dostatecznej liczby historii θ.</div>'}
        </div>
      </div>

      <div class="analytics-card">
        <h3>🎯 Umiejętność per Domena (Oś B)</h3>
        <table class="list-table">
          <thead><tr><th>Domena (Oś B)</th><th>θ domeny</th><th>Poprawność</th></tr></thead>
          <tbody>
            ${(data.domain_performance || []).map(d => `
              <tr>
                <td><strong>${d.axis_b}</strong></td>
                <td><kbd>θ = ${d.theta >= 0 ? '+' : ''}${typeof d.theta === 'number' ? d.theta.toFixed(3) : d.theta}</kbd></td>
                <td><span>${d.accuracy_pct}%</span> <span style="color:var(--text-muted); font-size:0.8rem;">(${d.total_attempts - d.error_count}/${d.total_attempts})</span></td>
              </tr>
            `).join('') || '<tr><td colspan="3" style="color:var(--text-muted)">Brak danych domenowych.</td></tr>'}
          </tbody>
        </table>
      </div>
    </div>

    <!-- 4. Hardest Questions & Recent Activity -->
    <div style="display: grid; grid-template-columns: 1fr 1fr; gap: 1.25rem; margin-bottom: 1.25rem;">
      <div class="analytics-card">
        <h3>🔥 Najtrudniejsze Pytania (Hardest)</h3>
        <table class="list-table">
          <thead><tr><th>ID</th><th>Treść pytania</th><th>% błędów (n prób)</th></tr></thead>
          <tbody>
            ${(data.hardest_questions || []).map(q => `
              <tr>
                <td>#${q.id}</td>
                <td><span style="color:var(--text-main); font-weight:500;">${q.q_pl.substring(0, 38)}...</span></td>
                <td><strong>${q.error_pct}%</strong> <span style="color:var(--text-muted); font-size:0.775rem;">(${q.attempts} prób)</span></td>
              </tr>
            `).join('') || '<tr><td colspan="3" style="color:var(--text-muted)">Brak wyliczonych trudności pytań.</td></tr>'}
          </tbody>
        </table>
      </div>

      <div class="analytics-card">
        <h3>📜 Ostatnie Odpowiedzi i Feed</h3>
        <table class="list-table">
          <thead>
            <tr>
              <th>ID</th>
              <th>Wybrana</th>
              <th>Wynik</th>
              <th>Czas</th>
            </tr>
          </thead>
          <tbody>
            ${(data.recent_activity || []).map(a => `
              <tr>
                <td>#${a.question_id}</td>
                <td><strong>${a.chosen}</strong></td>
                <td>${a.is_correct ? '<span style="color:var(--success); font-weight:600;">✓ OK</span>' : '<span style="color:var(--danger); font-weight:600;">✗ Błąd</span>'}</td>
                <td>${(a.time_ms / 1000).toFixed(1)}s</td>
              </tr>
            `).join('') || '<tr><td colspan="4" style="color:var(--text-muted)">Brak ostatnich odpowiedzi.</td></tr>'}
          </tbody>
        </table>
      </div>
    </div>

    <!-- 5. Weekly Readiness Check Instrument -->
    <div class="analytics-card" style="background: rgba(30, 41, 59, 0.4); border: 1px solid var(--card-border); padding: 1.5rem; margin-bottom: 1.25rem;">
      <div style="display: flex; justify-content: space-between; align-items: center;">
        <div>
          <h3 style="margin: 0; font-size: 1.2rem;">⏱️ Tygodniowy Sprawdzian (Przyrząd Pomiarowy Gotowości)</h3>
          <p style="color: var(--text-muted); font-size: 0.875rem; margin-top: 0.25rem;">
            Oficjalny arkusz 32 pytań (20 podstawowych + 12 specjalistycznych, próg zdawalności: 68/74 pkt). Służy wyłącznie do pomiaru postępu.
          </p>
        </div>
        <button class="answer-btn correct" style="padding: 0.6rem 1.25rem; font-size: 0.9rem;" onclick="startExamCheck()">
          📝 Uruchom Sprawdzian (32 pytania)
        </button>
      </div>
    </div>
  `;
}


// ---------------------------------------------------------------------------
// Weekly Readiness Exam Check Runner
// ---------------------------------------------------------------------------

async function startExamCheck() {
  if (!state.user) {
    openAuthModal('Zaloguj się, aby przystąpić do Tygodniowego Sprawdzianu.');
    return;
  }

  const modal = document.getElementById('exam-modal');
  const content = document.getElementById('exam-modal-content');
  if (!modal || !content) return;

  modal.style.display = 'flex';
  content.innerHTML = '<div style="text-align:center; padding: 2rem; color: var(--text-muted);">Generowanie arkusza sprawdzianu (32 pytania)...</div>';

  try {
    const res = await fetch('/api/exam/start', { method: 'POST' });
    if (!res.ok) {
      content.innerHTML = '<div style="color: var(--danger); padding: 1.5rem;">Wystąpił błąd przy pobieraniu arkusza egzaminacyjnego.</div>';
      return;
    }

    const data = await res.json();
    state.examState = {
      questions: data.questions,
      currentIndex: 0,
      answers: [],
      startTime: Date.now(),
      maxScore: data.max_score,
      passThreshold: data.pass_threshold
    };

    renderExamQuestion();
  } catch (err) {
    console.error("Failed to start exam check:", err);
  }
}

function renderExamQuestion() {
  const content = document.getElementById('exam-modal-content');
  if (!state.examState || !content) return;

  const es = state.examState;
  if (es.currentIndex >= es.questions.length) {
    finishExamCheck();
    return;
  }

  const q = es.questions[es.currentIndex];
  const qNum = es.currentIndex + 1;
  const isTN = q.type === 'TN';

  const mediaHtml = renderMedia(q);

  content.innerHTML = `
    <div style="display: flex; justify-content: space-between; align-items: center; margin-bottom: 1rem; border-bottom: 1px solid var(--card-border); padding-bottom: 0.75rem;">
      <div>
        <h3 style="margin: 0; font-size: 1.15rem;">📝 Tygodniowy Sprawdzian (Pytanie ${qNum} z ${es.questions.length})</h3>
        <span style="font-size: 0.8rem; color: var(--text-muted);">${q.scope} — Waga: <strong>${q.points} PKT</strong></span>
      </div>
      <button class="btn-secondary" style="font-size: 0.8rem;" onclick="closeExamModal()">Anuluj</button>
    </div>

    <div class="media-container" style="max-height: 280px; margin-bottom: 1rem;">${mediaHtml}</div>
    <div class="question-text" style="font-size: 1.1rem; margin-bottom: 1.25rem;">${q.q_pl}</div>

    <div class="answers-grid">
      ${isTN ? `
        <button class="answer-btn" onclick="recordExamAnswer(${q.id}, 'T')"><kbd>T</kbd> TAK</button>
        <button class="answer-btn" onclick="recordExamAnswer(${q.id}, 'N')"><kbd>N</kbd> NIE</button>
      ` : `
        <button class="answer-btn" onclick="recordExamAnswer(${q.id}, 'A')"><kbd>A</kbd> A: ${q.a_pl || ''}</button>
        <button class="answer-btn" onclick="recordExamAnswer(${q.id}, 'B')"><kbd>B</kbd> B: ${q.b_pl || ''}</button>
        <button class="answer-btn" onclick="recordExamAnswer(${q.id}, 'C')"><kbd>C</kbd> C: ${q.c_pl || ''}</button>
      `}
    </div>
  `;
}

function recordExamAnswer(questionId, chosen) {
  if (!state.examState) return;
  state.examState.answers.push({
    question_id: questionId,
    chosen: chosen,
    time_ms: 0
  });

  state.examState.currentIndex++;
  renderExamQuestion();
}

async function finishExamCheck() {
  const content = document.getElementById('exam-modal-content');
  if (!state.examState || !content) return;

  const es = state.examState;
  const elapsedSec = Math.round((Date.now() - es.startTime) / 1000);

  content.innerHTML = '<div style="text-align:center; padding: 2rem; color: var(--text-muted);">Przetwarzanie i ocenianie wyników sprawdzianu...</div>';

  try {
    const res = await fetch('/api/exam/submit', {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({
        answers: es.answers,
        time_seconds: elapsedSec
      })
    });

    const report = await res.json();
    state.examState = null;

    content.innerHTML = `
      <div style="text-align: center; padding: 1.5rem 0;">
        <h2 style="font-size: 1.8rem; margin-bottom: 0.5rem;">
          ${report.passed ? '🎉 <span style="color: var(--success);">ZDAŁEŚ SPRAWDZIAN!</span>' : '❌ <span style="color: var(--danger);">NIE ZDAŁEŚ</span>'}
        </h2>
        <div style="font-size: 2.5rem; font-weight: 800; margin: 1rem 0; color: var(--text-main);">
          ${report.score} / ${report.max_score} <span style="font-size: 1.1rem; color: var(--text-muted); font-weight: 400;">PKT</span>
        </div>
        <p style="color: var(--text-muted); margin-bottom: 1.5rem;">
          Próg zdawalności: ${es.passThreshold} pkt | Czas trwania: ${Math.floor(elapsedSec / 60)}m ${elapsedSec % 60}s | Poprawnych: ${report.correct_count} z ${report.total_questions}
        </p>

        <button class="answer-btn correct" style="max-width: 240px; margin: 0 auto;" onclick="closeExamModal(); loadDashboard();">Zamknij i przejdź do Pulpitu</button>
      </div>
    `;
  } catch (err) {
    console.error("Failed to submit exam check:", err);
  }
}

function closeExamModal() {
  const modal = document.getElementById('exam-modal');
  if (modal) modal.style.display = 'none';
  state.examState = null;
}


