const form = document.getElementById('chat-form');
const messages = document.getElementById('messages');
const promptEl = document.getElementById('prompt');
const sendBtn = document.getElementById('send');

function addMessage(text, cls = 'bot'){
  const div = document.createElement('div');
  div.className = 'bubble ' + cls;
  div.innerHTML = text;
  messages.appendChild(div);
  messages.scrollTop = messages.scrollHeight;
  return div;
}

function formatDocResult(r, i){
  return `
<div class="result-item">
  <div class="result-header">
    <span class="result-number">Result ${i}</span>
    <span class="result-score">Score: ${(+r.score).toFixed(1)}%</span>
  </div>
  <strong>${r.title || 'Document'}</strong>
  <p>${r.text}</p>
</div>
  `.trim();
}

form.addEventListener('submit', async (e) =>{
  e.preventDefault();
  const prompt = promptEl.value.trim();
  if(!prompt) return;
  
  // Disable input
  promptEl.disabled = true;
  sendBtn.disabled = true;
  
  // Add user message
  addMessage(prompt, 'user');
  promptEl.value = '';
  
  // Add loading state
  const loadingBubble = addMessage('<div class="spinner"></div><span>Generating answer from knowledge base...</span>', 'bot');
  
  try{
    const res = await fetch('/query', {
      method: 'POST',
      headers: {'Content-Type': 'application/json'},
      body: JSON.stringify({question: prompt, k: 3})
    });
    
    // Check if response is OK
    if (!res.ok) {
      const errorData = await res.json();
      throw new Error(errorData.detail || `API Error: ${res.status}`);
    }
    
    const data = await res.json();
    
    // remove loading bubble
    loadingBubble.remove();

    // Check if API returned an error in the response
    if (data.error) {
      addMessage('❌ ' + data.error, 'bot');
      return;
    }

    if(data.answer){
      // Display the AI-generated answer prominently
      const answerHTML = `
<div class="ai-answer">
  <div class="answer-content">
    ${data.answer.replace(/\n/g, '<br>')}
  </div>
  <div class="answer-footer">
    📚 Based on ${data.source_count} document(s)
  </div>
</div>
      `;
      addMessage(answerHTML, 'bot');
      
      // Show sources below
      if(data.sources && data.sources.length){
        const sourceHTML = `
<div class="sources-container">
  <details>
    <summary>📖 View Source Documents (${data.sources.length})</summary>
    <div class="sources-list">
      ${data.sources.map((r, i) => `
      <div class="source-item">
        <div class="source-header">
          <span class="source-number">Source ${i + 1}</span>
          <span class="source-score">Match Score: ${(+r.score).toFixed(1)}%</span>
        </div>
        <strong>${r.title || 'Document'}</strong>
        <p>${r.text}</p>
      </div>
      `).join('')}
    </div>
  </details>
</div>
        `;
        addMessage(sourceHTML, 'bot');
      }
    } else if(data.sources && data.sources.length) {
      // If LLM failed but we have sources, show them
      addMessage('📚 Could not generate answer, but found relevant documents:', 'bot');
      const sourceHTML = `
<div class="sources-container">
  <div class="sources-list">
    ${data.sources.map((r, i) => `
    <div class="source-item">
      <div class="source-header">
        <span class="source-number">Source ${i + 1}</span>
        <span class="source-score">Match Score: ${(+r.score).toFixed(1)}%</span>
      </div>
      <strong>${r.title || 'Document'}</strong>
      <p>${r.text}</p>
    </div>
    `).join('')}
  </div>
</div>
      `;
      addMessage(sourceHTML, 'bot');
    } else {
      addMessage('❌ No results found. Try rephrasing your question.', 'bot');
    }
  }catch(err){
    loadingBubble.remove();
    console.error('Error:', err);
    addMessage('❌ Error: ' + (err.message || 'Unknown error occurred'), 'bot');
  }finally{
    // Re-enable input
    promptEl.disabled = false;
    sendBtn.disabled = false;
    promptEl.focus();
  }
});

// allow Enter to send (Shift+Enter for newline)
promptEl.addEventListener('keydown', (e)=>{
  if(e.key === 'Enter' && !e.shiftKey){
    e.preventDefault();
    form.requestSubmit();
  }
});

// Auto-resize textarea
promptEl.addEventListener('input', () => {
  promptEl.style.height = 'auto';
  promptEl.style.height = Math.min(promptEl.scrollHeight, 120) + 'px';
});

// Focus on load
window.addEventListener('load', () => promptEl.focus());

