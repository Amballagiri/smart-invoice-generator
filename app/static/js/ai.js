(() => {
  const page = document.querySelector('[data-ai-chat]');
  if (!page) return;
  const messages = document.querySelector('#aiMessages');
  const form = document.querySelector('#aiComposer');
  const input = document.querySelector('#aiMessage');
  const send = document.querySelector('#aiSend');
  const csrf = document.querySelector('#csrfToken').value;
  const escapeHtml = value => value.replace(/[&<>'"]/g, char => ({'&':'&amp;','<':'&lt;','>':'&gt;',"'":'&#39;','"':'&quot;'}[char]));
  const markdown = text => escapeHtml(text).replace(/```([\s\S]*?)```/g, '<pre><code>$1</code></pre>').replace(/`([^`]+)`/g, '<code>$1</code>').replace(/\*\*([^*]+)\*\*/g, '<strong>$1</strong>').replace(/^###? (.+)$/gm, '<strong>$1</strong>').replace(/^- (.+)$/gm, '<li>$1</li>').replace(/(<li>[\s\S]*?<\/li>)(?:\n|$)/g, '$1').replace(/\n/g, '<br>');
  const scroll = () => { messages.scrollTop = messages.scrollHeight; };
  const addMessage = (text, role, typing = false) => {
    document.querySelector('#aiEmpty')?.remove();
    const article = document.createElement('article');
    article.className = `chat-message chat-message-${role}`;
    const avatar = role === 'user' ? 'You' : '<i class="bi bi-robot"></i>';
    article.innerHTML = `<div class="chat-avatar">${avatar}</div><div class="message-bubble">${role === 'assistant' && !typing ? '<button class="copy-message" type="button" title="Copy response"><i class="bi bi-copy"></i></button>' : ''}<div class="message-content ${role === 'assistant' ? 'markdown-content' : ''}">${typing ? '<span class="typing-dots"><i></i><i></i><i></i></span>' : role === 'assistant' ? markdown(text) : escapeHtml(text)}</div></div>`;
    messages.append(article); scroll(); return article;
  };
  const resize = () => { input.style.height = 'auto'; input.style.height = `${Math.min(input.scrollHeight, 180)}px`; };
  messages.querySelectorAll('[data-markdown]').forEach(node => { node.innerHTML = markdown(node.textContent); });
  scroll(); resize();
  input.addEventListener('input', resize);
  input.addEventListener('keydown', event => {
    if (event.key === 'Enter' && !event.shiftKey) {
      event.preventDefault();
      form.dispatchEvent(new Event('submit'));
    }
  });
  document.querySelectorAll('.prompt-chips button').forEach(button => button.addEventListener('click', () => { input.value = button.textContent; resize(); input.focus(); }));
  messages.addEventListener('click', event => { const button = event.target.closest('.copy-message'); if (!button) return; navigator.clipboard.writeText(button.parentElement.querySelector('.message-content').innerText); button.innerHTML = '<i class="bi bi-check2"></i>'; setTimeout(() => { button.innerHTML = '<i class="bi bi-copy"></i>'; }, 1200); });
  form.addEventListener('submit', async event => { event.preventDefault(); const value = input.value.trim(); if (!value || send.disabled) return; addMessage(value, 'user'); input.value = ''; resize(); send.disabled = true; const pending = addMessage('', 'assistant', true); try { const response = await fetch(page.dataset.messageUrl, {method: 'POST', headers: {'Content-Type': 'application/json', 'X-CSRFToken': csrf}, body: JSON.stringify({message: value})}); const data = await response.json(); if (!response.ok || !data.ok) throw new Error(data.error || 'Unable to send message.'); pending.remove(); addMessage(data.answer, 'assistant'); } catch (error) { pending.remove(); addMessage(`**Unable to respond:** ${error.message}`, 'assistant'); } finally { send.disabled = false; input.focus(); } });
})();
