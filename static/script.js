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

  var isFullLayout = (function () {
    var params = new URLSearchParams(window.location.search);
    var explicitPopup = params.get('layout') === 'popup';
    var full = !explicitPopup;
    if (full) {
      document.body.classList.add('layout-full', 'show-chatbot');
    }
    return full;
  })();

  var layoutSwitch = document.getElementById('layout-switch');
  if (layoutSwitch) {
    layoutSwitch.textContent = isFullLayout ? 'Всплывающее окно' : 'Полноэкранный';
    var basePath = window.location.pathname || '/';
    layoutSwitch.href = isFullLayout ? (basePath + (basePath.indexOf('?') >= 0 ? '&' : '?') + 'layout=popup') : basePath.split('?')[0];
    layoutSwitch.addEventListener('click', function (e) {
      e.preventDefault();
      window.location.href = layoutSwitch.href;
    });
  }

  function escapeHtml(s) {
    return String(s)
      .replace(/&/g, '&amp;')
      .replace(/</g, '&lt;')
      .replace(/>/g, '&gt;')
      .replace(/"/g, '&quot;');
  }

  function formatBold(text) {
    if (!text) return '';
    var escaped = escapeHtml(text);
    return escaped.replace(/\*\*(.+?)\*\*/g, '<strong>$1</strong>');
  }

  function createMessageElement(content, role) {
    const div = document.createElement('div');
    div.className = 'message ' + (role === 'user' ? 'user-message' : 'bot-message');
    const text = document.createElement('div');
    text.className = 'message-text';
    if (role === 'bot') {
      text.innerHTML = formatBold(content);
    } else {
      text.textContent = content;
    }
    div.appendChild(text);
    return { wrap: div, text };
  }

  function appendStreamChunk(element, chunk, formattedSetter) {
    if (chunk == null || chunk === '') return;
    if (formattedSetter) {
      formattedSetter(chunk);
    } else {
      element.textContent = (element.textContent || '') + chunk;
    }
  }

  var MAX_MESSAGE_LENGTH = 1000;
  var MAX_LENGTH_MSG = 'Размер сообщения ограничен 1000 символами.';

  async function handleSend(e) {
    e.preventDefault();
    const text = messageInput.value.trim();
    if (!text) return;
    if (text.length > MAX_MESSAGE_LENGTH) {
      errorEl.textContent = MAX_LENGTH_MSG;
      return;
    }
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
        var errMsg = res.status === 422 ? MAX_LENGTH_MSG : (err.detail || res.statusText);
        if (typeof errMsg !== 'string' && Array.isArray(errMsg)) errMsg = errMsg[0] && errMsg[0].msg ? errMsg[0].msg : MAX_LENGTH_MSG;
        botEl.text.textContent = res.status === 422 ? '' : 'Ошибка: ' + errMsg;
        errorEl.textContent = res.status === 422 ? MAX_LENGTH_MSG : errMsg;
        sendBtn.disabled = false;
        return;
      }

      var streamedText = '';
      var pendingBuffer = '';
      var streamEnded = false;
      var typewriterMs = 18;
      var typewriterCharsPerTick = 2;

      function appendChunk(chunk) {
        pendingBuffer += chunk;
      }

      function drainTypewriter() {
        if (pendingBuffer.length === 0) {
          if (streamEnded) clearInterval(typewriterInterval);
          return;
        }
        var take = Math.min(typewriterCharsPerTick, pendingBuffer.length);
        streamedText += pendingBuffer.slice(0, take);
        pendingBuffer = pendingBuffer.slice(take);
        botEl.text.innerHTML = formatBold(streamedText);
        chatBody.scrollTo({ top: chatBody.scrollHeight, behavior: 'smooth' });
      }

      var typewriterInterval = setInterval(drainTypewriter, typewriterMs);

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
            appendChunk(data);
          }
        }
      }
      streamEnded = true;
      if (pendingBuffer.length === 0) clearInterval(typewriterInterval);
    } catch (err) {
      botEl.wrap.classList.remove('thinking');
      botEl.text.textContent = 'Ошибка: ' + (err.message || 'сеть');
      errorEl.textContent = err.message || 'Ошибка запроса';
      if (typeof typewriterInterval !== 'undefined') clearInterval(typewriterInterval);
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

  function checkLengthWarning() {
    if (messageInput.value.length >= MAX_MESSAGE_LENGTH) {
      errorEl.textContent = MAX_LENGTH_MSG;
    } else if (errorEl.textContent === MAX_LENGTH_MSG) {
      errorEl.textContent = '';
    }
  }

  messageInput.addEventListener('input', function () {
    setTimeout(checkLengthWarning, 0);
  });

  messageInput.addEventListener('paste', function () {
    setTimeout(checkLengthWarning, 0);
    setTimeout(checkLengthWarning, 50);
  });

  var welcomeText = 'Здравствуйте! Я — умный помощник компании «Клиентариум». Мы создаем ИИ-агентов, которые берут на себя рутину: разгружают поддержку до 60%, прогревают лидов в 2 раза быстрее и автоматизируют маркетинг. Подскажите, в какой сфере работает ваша компания? Это поможет мне сразу привести самые релевантные примеры.';
  var welcomeDelayMs = 2500;
  setTimeout(function () {
    var welcome = createMessageElement(welcomeText, 'bot');
    chatBody.appendChild(welcome.wrap);
  }, welcomeDelayMs);
})();
