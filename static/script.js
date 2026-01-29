/**
 * AI Chatbot: дизайн в стиле CodingNepal, автогенерация session_id, пробелы в ответах.
 */
(function () {
  const chatBody = document.querySelector('.chat-body');
  const messageInput = document.querySelector('.message-input');
  const chatForm = document.querySelector('.chat-form');
  const sendBtn = document.querySelector('.send-btn');
  const chatbotToggler = document.getElementById('chatbot-toggler');
  const closeChatbot = document.getElementById('close-chatbot');
  const errorEl = document.querySelector('.error-msg');

  // Уникальный идентификатор сессии создаётся автоматически при загрузке
  function getOrCreateSessionId() {
    const key = 'aichatbot_session_id';
    let sid = sessionStorage.getItem(key);
    if (!sid) {
      sid = typeof crypto !== 'undefined' && crypto.randomUUID ? crypto.randomUUID() : 's-' + Date.now() + '-' + Math.random().toString(36).slice(2, 11);
      sessionStorage.setItem(key, sid);
    }
    return sid;
  }

  const sessionId = getOrCreateSessionId();
  const userId = 'user-' + sessionId.slice(0, 8);

  function createMessageElement(content, role) {
    const div = document.createElement('div');
    div.className = 'message ' + (role === 'user' ? 'user-message' : 'bot-message');
    const text = document.createElement('div');
    text.className = 'message-text';
    text.textContent = content;
    div.appendChild(text);
    return { wrap: div, text };
  }

  function isWordChar(c) {
    if (!c) return false;
    var code = c.charCodeAt(0);
    return (code >= 48 && code <= 57) || (code >= 65 && code <= 90) || (code >= 97 && code <= 122) || (code >= 0x0400 && code <= 0x04FF) || c === '_';
  }

  function appendStreamChunk(element, chunk) {
    var text = element.textContent || '';
    if (chunk === '') return;
    if (text.length > 0) {
      var lastChar = text[text.length - 1];
      var firstChar = chunk.charAt(0);
      if (isWordChar(lastChar) && isWordChar(firstChar)) {
        chunk = ' ' + chunk;
      }
    }
    element.textContent = text + chunk;
  }

  async function handleSend(e) {
    e.preventDefault();
    const text = messageInput.value.trim();
    if (!text) return;
    messageInput.value = '';
    errorEl.textContent = '';

    const userEl = createMessageElement(text, 'user');
    chatBody.appendChild(userEl.wrap);
    chatBody.scrollTo({ top: chatBody.scrollHeight, behavior: 'smooth' });

    const botEl = createMessageElement('', 'bot');
    botEl.wrap.classList.add('thinking');
    botEl.text.innerHTML = '<div class="thinking-indicator"><span class="dot"></span><span class="dot"></span><span class="dot"></span></div>';
    chatBody.appendChild(botEl.wrap);
    chatBody.scrollTo({ top: chatBody.scrollHeight, behavior: 'smooth' });

    sendBtn.disabled = true;

    try {
      const res = await fetch('/api/chat', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({
          user_id: userId,
          message: text,
          dialog_id: sessionId,
        }),
      });

      botEl.wrap.classList.remove('thinking');
      botEl.text.innerHTML = '';
      botEl.text.textContent = '';

      if (!res.ok) {
        const err = await res.json().catch(() => ({ detail: res.statusText }));
        botEl.text.textContent = 'Ошибка: ' + (err.detail || res.statusText);
        errorEl.textContent = err.detail || res.statusText;
        sendBtn.disabled = false;
        return;
      }

      const reader = res.body.getReader();
      const dec = new TextDecoder();
      let buffer = '';
      while (true) {
        const { done, value } = await reader.read();
        if (done) break;
        buffer += dec.decode(value, { stream: true });
        const lines = buffer.split('\n');
        buffer = lines.pop() || '';
        for (const line of lines) {
          if (line.startsWith('data: ')) {
            var data = line.slice(6).replace(/\r?\n$/, '');
            if (data.trim() === '[DONE]') continue;
            appendStreamChunk(botEl.text, data);
            chatBody.scrollTo({ top: chatBody.scrollHeight, behavior: 'smooth' });
          }
        }
      }
    } catch (err) {
      botEl.wrap.classList.remove('thinking');
      botEl.text.textContent = 'Ошибка: ' + (err.message || 'сеть');
      errorEl.textContent = err.message || 'Ошибка запроса';
    } finally {
      sendBtn.disabled = false;
      chatBody.scrollTo({ top: chatBody.scrollHeight, behavior: 'smooth' });
    }
  }

  chatForm.addEventListener('submit', handleSend);
  closeChatbot.addEventListener('click', () => document.body.classList.remove('show-chatbot'));
  chatbotToggler.addEventListener('click', () => document.body.classList.toggle('show-chatbot'));

  messageInput.addEventListener('keydown', function (e) {
    if (e.key === 'Enter' && !e.shiftKey) {
      e.preventDefault();
      handleSend(e);
    }
  });

  const welcome = createMessageElement('Привет! Чем могу помочь?', 'bot');
  chatBody.appendChild(welcome.wrap);
})();
