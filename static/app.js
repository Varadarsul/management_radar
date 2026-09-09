const chatForm = document.getElementById('chat-form');
const questionInput = document.getElementById('question-input');
const chatLog = document.getElementById('chat-log');
const companyButtons = document.querySelectorAll('.company-chip');

function appendMessage(text, sender = 'bot') {
  const div = document.createElement('div');
  div.className = `message ${sender}`;
  div.textContent = text;
  chatLog.appendChild(div);
  chatLog.scrollTop = chatLog.scrollHeight;
}

function buildTimeline(records) {
  const timeline = document.getElementById('timeline-items');
  if (!records || !records.length) {
    timeline.innerHTML = '<p>No sources found for this company.</p>';
    return;
  }

  timeline.innerHTML = records
    .map((source) => `
      <article class="timeline-item">
        <div class="dot"></div>
        <div class="content-box">
          <div class="meta-row">
            <span class="pill">${source.type}</span>
            <span>${source.company}</span>
            <span>${source.date || 'Recent'}</span>
          </div>
          <h3>${source.title}</h3>
          <p>${(source.content || 'Source loaded successfully.').slice(0, 220)}</p>
          <a href="${source.url}" target="_blank" rel="noreferrer">Open source</a>
        </div>
      </article>
    `)
    .join('');
}

async function setCompany(companyId) {
  companyButtons.forEach((button) => {
    button.classList.toggle('active', Number(button.dataset.companyId) === Number(companyId));
  });

  const response = await fetch('/api/companies');
  const data = await response.json();
  const company = data.companies.find((entry) => Number(entry.id) === Number(companyId));
  if (company) {
    const formatted = company.sources.map((source) => ({
      ...source,
      company: company.name,
    }));
    buildTimeline(formatted);
  }
}

companyButtons.forEach((button) => {
  button.addEventListener('click', () => setCompany(button.dataset.companyId));
});

chatForm.addEventListener('submit', async (event) => {
  event.preventDefault();
  const text = questionInput.value.trim();
  if (!text) return;

  appendMessage(text, 'user');
  questionInput.value = '';
  appendMessage('Checking the local source cache...', 'bot');

  try {
    const response = await fetch('/api/chat', {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ question: text }),
    });
    const payload = await response.json();
    const messages = payload.results || [];
    chatLog.lastElementChild.remove();
    appendMessage(payload.answer, 'bot');

    if (messages.length) {
      const evidence = messages
        .slice(0, 3)
        .map((item) => `${item.company} — ${item.title}: ${item.snippet}`)
        .join('\n');
      appendMessage(`Evidence: ${evidence}`, 'bot');
    }
  } catch (error) {
    chatLog.lastElementChild.remove();
    appendMessage('The system could not answer that request right now.', 'bot');
  }
});

if (companyButtons.length) {
  setCompany(companyButtons[0].dataset.companyId);
}
