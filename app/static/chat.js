const form = document.getElementById('chat-form');
const messages = document.getElementById('messages');
const promptEl = document.getElementById('prompt');
const sendBtn = document.getElementById('send');
const modelBtn = document.getElementById('model-btn');
const modelMenu = document.getElementById('model-menu');
const llmNote = document.getElementById('llm-note');
let selectedModelId = null;

function escapeHtml(str) {
  if (str == null) return '';
  const d = document.createElement('div');
  d.textContent = String(str);
  return d.innerHTML;
}

function nl2br(escaped) {
  return escaped.replace(/\n/g, '<br>');
}

function matchPercent(score) {
  const value = Number(score);
  if (!Number.isFinite(value)) return 'n/a';
  return `${(Math.max(0, Math.min(1, value)) * 100).toFixed(1)}%`;
}

/**
 * @param {'user'|'bot'} role
 * @param {string} content — plain text or HTML if richHtml
 * @param {{ richHtml?: boolean, isError?: boolean }} opts
 * @returns {HTMLElement} row element (for removal)
 */
function appendMessage(role, content, opts = {}) {
  const { richHtml = false, isError = false } = opts;
  const row = document.createElement('div');
  row.className = `msg-row msg-row--${role}`;
  if (isError) row.classList.add('msg-error');

  const avatar = document.createElement('div');
  avatar.className = 'msg-avatar';
  avatar.setAttribute('aria-hidden', 'true');
  if (role === 'user') {
    avatar.innerHTML =
      '<svg width="18" height="18" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" aria-hidden="true"><path d="M20 21v-2a4 4 0 0 0-4-4H8a4 4 0 0 0-4 4v2"/><circle cx="12" cy="7" r="4"/></svg>';
  } else {
    avatar.innerHTML =
      '<svg width="18" height="18" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round" aria-hidden="true"><path d="M21 15a2 2 0 0 1-2 2H7l-4 4V5a2 2 0 0 1 2-2h14a2 2 0 0 1 2 2z"/></svg>';
  }

  const body = document.createElement('div');
  body.className = 'msg-body';

  const label = document.createElement('span');
  label.className = 'msg-label';
  label.textContent = role === 'user' ? 'You' : 'Assistant';

  const bubble = document.createElement('div');
  bubble.className = 'bubble' + (richHtml ? ' bot-rich' : '');
  if (richHtml) bubble.innerHTML = content;
  else bubble.innerHTML = nl2br(escapeHtml(content));

  body.appendChild(label);
  body.appendChild(bubble);
  row.appendChild(avatar);
  row.appendChild(body);
  messages.appendChild(row);
  scrollThreadToEnd();
  return row;
}

function scrollThreadToEnd() {
  const stage = document.querySelector('.stage');
  const snap = () => {
    if (!stage) return;
    stage.scrollTop = stage.scrollHeight;
  };
  snap();
  requestAnimationFrame(snap);
}

const emptyState = document.getElementById('empty');

function closeModelMenu() {
  modelMenu.hidden = true;
  modelBtn.setAttribute('aria-expanded', 'false');
}

function renderModelMenu(options, defaultId) {
  modelMenu.innerHTML = '';
  if (!options.length) {
    const empty = document.createElement('div');
    empty.className = 'model-empty';
    empty.textContent = 'No models wired.';
    modelMenu.appendChild(empty);
    modelBtn.textContent = 'Models';
    selectedModelId = null;
    return;
  }
  const availableDefault = options.find((o) => o.id === defaultId && o.available !== false);
  selectedModelId = availableDefault
    ? availableDefault.id
    : (options.find((o) => o.available !== false) || options[0]).id;
  const current = options.find((o) => o.id === selectedModelId);
  modelBtn.textContent = current ? current.label : 'Models';
  for (const option of options) {
    const item = document.createElement('button');
    item.type = 'button';
    item.className = 'model-option';
    item.setAttribute('role', 'option');
    item.setAttribute('aria-selected', option.id === selectedModelId ? 'true' : 'false');
    if (option.available === false) item.disabled = false;
    const status = option.available === false ? ' · not enabled' : '';
    item.textContent = option.label + status;
    item.addEventListener('click', () => {
      selectedModelId = option.id;
      modelBtn.textContent = option.label;
      closeModelMenu();
      for (const el of modelMenu.querySelectorAll('.model-option')) {
        el.setAttribute('aria-selected', el.dataset.id === option.id ? 'true' : 'false');
      }
    });
    item.dataset.id = option.id;
    modelMenu.appendChild(item);
  }
}

async function loadLlmOptions() {
  try {
    const res = await fetch('/llm/options');
    const data = await res.json();
    renderModelMenu(data.options || [], data.default);
    llmNote.textContent = '';
  } catch (e) {
    llmNote.textContent = 'Could not load models.';
    console.warn(e);
  }
}

modelBtn.addEventListener('click', () => {
  const open = modelMenu.hidden;
  modelMenu.hidden = !open;
  modelBtn.setAttribute('aria-expanded', open ? 'true' : 'false');
});

document.addEventListener('click', (event) => {
  if (!modelBtn.contains(event.target) && !modelMenu.contains(event.target)) {
    closeModelMenu();
  }
});

/**
 * POST /query/stream: consumes SSE until a single `data:` JSON payload (same shape as /query).
 */
async function fetchQueryWithKeepalive(prompt, k, llmId) {
  const payload = { question: prompt, k };
  if (llmId) {
    payload.llm_id = llmId;
  }
  const res = await fetch('/query/stream', {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify(payload),
  });
  if (!res.ok) {
    let detail = `API Error: ${res.status}`;
    try {
      const errJson = await res.json();
      detail = errJson.detail || detail;
    } catch (_) {
      /* ignore */
    }
    throw new Error(detail);
  }
  const reader = res.body.getReader();
  const decoder = new TextDecoder();
  let buffer = '';
  let dataPayload = null;
  while (true) {
    const { done, value } = await reader.read();
    if (value) {
      buffer += decoder.decode(value, { stream: true });
    }
    let sep;
    while ((sep = buffer.indexOf('\n\n')) >= 0) {
      const rawEvent = buffer.slice(0, sep);
      buffer = buffer.slice(sep + 2);
      for (const line of rawEvent.split('\n')) {
        if (line.startsWith('data:')) {
          const jsonText = line.slice(5).trim();
          if (jsonText) {
            dataPayload = JSON.parse(jsonText);
          }
        }
      }
    }
    if (done) {
      break;
    }
  }
  if (!dataPayload) {
    throw new Error('Empty or invalid stream response from server');
  }
  return dataPayload;
}

form.addEventListener('submit', async (e) => {
  e.preventDefault();
  const prompt = promptEl.value.trim();
  if (!prompt) return;

  promptEl.disabled = true;
  sendBtn.disabled = true;

  if (emptyState) emptyState.hidden = true;
  appendMessage('user', prompt);

  const loadingHtml = `<span class="loading-inner">…</span>`;
  const loadingRow = appendMessage('bot', loadingHtml, { richHtml: true });

  promptEl.value = '';

  try {
    const data = await fetchQueryWithKeepalive(prompt, 3, selectedModelId);
    loadingRow.remove();

    if (data.error) {
      appendMessage('bot', data.error, { isError: true });
    }

    const sources = Array.isArray(data.sources) ? data.sources : [];
    const sourceCount = Number(data.source_count || sources.length || 0);

    if (data.answer && !data.error) {
      const bodyHtml = nl2br(escapeHtml(data.answer));
      const footer =
        sourceCount > 0
          ? `<div class="answer-footer">Based on ${sourceCount} retrieved passage(s).</div>`
          : '';
      const answerHTML = `
<div class="ai-answer">
  <div class="answer-content">${bodyHtml}</div>
  ${footer}
</div>`;
      appendMessage('bot', answerHTML, { richHtml: true });

      if (sources.length) {
        const sourceHTML = `
<div class="sources-container">
  <details>
    <summary>View source documents (${sources.length})</summary>
    <div class="sources-list">
      ${sources
        .map(
          (r, i) => `
      <div class="source-item">
        <div class="source-header">
          <span class="source-number">Source ${i + 1}</span>
          <span class="source-score">Match: ${matchPercent(r.score)}</span>
        </div>
        <strong>${escapeHtml(r.title || 'Document')}</strong>
        <p>${escapeHtml(r.text || '')}</p>
      </div>`,
        )
        .join('')}
    </div>
  </details>
</div>`;
        appendMessage('bot', sourceHTML, { richHtml: true });
      }
    } else if (sources.length) {
      appendMessage(
        'bot',
        'Could not generate an answer, but these documents matched your question:',
      );
      const sourceHTML = `
<div class="sources-container">
  <div class="sources-list">
    ${data.sources
      .map(
        (r, i) => `
    <div class="source-item">
      <div class="source-header">
        <span class="source-number">Source ${i + 1}</span>
        <span class="source-score">Match: ${matchPercent(r.score)}</span>
      </div>
      <strong>${escapeHtml(r.title || 'Document')}</strong>
      <p>${escapeHtml(r.text || '')}</p>
    </div>`,
      )
      .join('')}
  </div>
</div>`;
      appendMessage('bot', sourceHTML, { richHtml: true });
    } else if (!data.error) {
      appendMessage('bot', 'No results found. Try rephrasing your question.', { isError: true });
    }
  } catch (err) {
    loadingRow.remove();
    console.error('Error:', err);
    appendMessage('bot', err.message || 'Unknown error occurred', { isError: true });
  } finally {
    promptEl.disabled = false;
    sendBtn.disabled = false;
    promptEl.focus();
  }
});

promptEl.addEventListener('keydown', (e) => {
  if (e.key === 'Enter' && !e.shiftKey) {
    e.preventDefault();
    form.requestSubmit();
  }
});

promptEl.addEventListener('input', () => {
  promptEl.style.height = 'auto';
  promptEl.style.height = Math.min(promptEl.scrollHeight, 140) + 'px';
});

window.addEventListener('load', () => {
  loadLlmOptions();
  promptEl.focus();
});
