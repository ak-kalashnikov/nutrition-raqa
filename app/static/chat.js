const form = document.getElementById('chat-form');
const messages = document.getElementById('messages');
const promptEl = document.getElementById('prompt');
const sendBtn = document.getElementById('send');
const suggestionsEl = document.getElementById('suggestions');
const llmSelect = document.getElementById('llm-select');
const llmNote = document.getElementById('llm-note');

function escapeHtml(str) {
  if (str == null) return '';
  const d = document.createElement('div');
  d.textContent = String(str);
  return d.innerHTML;
}

function nl2br(escaped) {
  return escaped.replace(/\n/g, '<br>');
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
  messages.scrollTop = messages.scrollHeight;
  return row;
}

appendMessage(
  'bot',
  "Hi! I'm your nutrition and sports health assistant. I can explain nutrients, macros, training fuel, hydration, and general sports nutrition.\n\nI can't give medical advice or emergency help. For diagnoses, medication, or urgent issues, please contact a licensed professional.",
);

async function loadLlmOptions() {
  try {
    const res = await fetch('/llm/options');
    const data = await res.json();
    llmSelect.innerHTML = '';
    const opts = data.options || [];
    for (const o of opts) {
      const opt = document.createElement('option');
      opt.value = o.id;
      opt.textContent = o.label;
      llmSelect.appendChild(opt);
    }
    if (data.default && opts.some((o) => o.id === data.default)) {
      llmSelect.value = data.default;
    }
    llmNote.textContent =
      opts.length === 0
        ? 'Server has no LLM API keys — add GROQ_API_KEY, HF_TOKEN, or GEMINI_API_KEY.'
        : 'Free-tier quotas apply.';
  } catch (e) {
    llmNote.textContent = 'Could not load model list.';
    console.warn(e);
  }
}

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

suggestionsEl.addEventListener('click', (e) => {
  const chip = e.target.closest('.chip');
  if (!chip) return;
  const q = chip.getAttribute('data-q');
  if (!q) return;
  promptEl.value = q;
  promptEl.dispatchEvent(new Event('input'));
  promptEl.focus();
});

form.addEventListener('submit', async (e) => {
  e.preventDefault();
  const prompt = promptEl.value.trim();
  if (!prompt) return;

  promptEl.disabled = true;
  sendBtn.disabled = true;

  appendMessage('user', prompt);

  const loadingHtml = `
    <div class="loading-inner">
      <div class="loading-dots" aria-hidden="true"><span></span><span></span><span></span></div>
      <span>Searching the knowledge base and drafting an answer…</span>
    </div>
  `;
  const loadingRow = appendMessage('bot', loadingHtml, { richHtml: true });

  promptEl.value = '';

  try {
    const data = await fetchQueryWithKeepalive(prompt, 3, llmSelect.value || null);
    loadingRow.remove();

    if (data.error) {
      appendMessage('bot', data.error, { isError: true });
      return;
    }

    if (data.answer) {
      const bodyHtml = nl2br(escapeHtml(data.answer));
      const answerHTML = `
<div class="ai-answer">
  <div class="answer-content">${bodyHtml}</div>
  <div class="answer-footer">Based on ${data.source_count} document(s) in the index.</div>
</div>`;
      appendMessage('bot', answerHTML, { richHtml: true });

      if (data.sources && data.sources.length) {
        const sourceHTML = `
<div class="sources-container">
  <details>
    <summary>View source documents (${data.sources.length})</summary>
    <div class="sources-list">
      ${data.sources
        .map(
          (r, i) => `
      <div class="source-item">
        <div class="source-header">
          <span class="source-number">Source ${i + 1}</span>
          <span class="source-score">Match: ${Number(r.score).toFixed(1)}%</span>
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
    } else if (data.sources && data.sources.length) {
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
        <span class="source-score">Match: ${(Math.max(0, Math.min(1, Number(r.score))) * 100).toFixed(1)}%</span>
      </div>
      <strong>${escapeHtml(r.title || 'Document')}</strong>
      <p>${escapeHtml(r.text || '')}</p>
    </div>`,
      )
      .join('')}
  </div>
</div>`;
      appendMessage('bot', sourceHTML, { richHtml: true });
    } else {
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
