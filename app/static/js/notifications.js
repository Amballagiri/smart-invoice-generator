document.addEventListener('DOMContentLoaded', function () {
  const apiPath = '/notifications/api';
  const defaultAnchor = document.querySelector('.notification-button');

  function buildDropdown() {
    const container = document.createElement('div');
    container.className = 'dropdown notification-dropdown';
    container.innerHTML = `
      <button id="notificationsToggle" class="btn btn-ghost" data-bs-toggle="dropdown" aria-expanded="false" aria-label="Notifications">
        <i class="bi bi-bell"></i>
        <span class="notif-badge" id="notifCount">0</span>
      </button>
      <div class="dropdown-menu dropdown-menu-end p-0" id="notificationsDropdown" style="width:360px;">
        <div class="dropdown-header d-flex justify-content-between align-items-center p-3">
          <strong>Notifications</strong>
          <div>
            <button class="btn btn-sm btn-link" id="markAllReadBtn">Mark all read</button>
            <button class="btn btn-sm btn-link text-danger" id="clearAllBtn">Clear</button>
          </div>
        </div>
        <div id="notificationsList" class="list-group list-group-flush"></div>
        <div class="dropdown-footer p-2 text-center"><a href="/notifications">View all notifications</a></div>
      </div>
    `;
    return container;
  }

  function upgradeAnchor() {
    const anchor = defaultAnchor;
    if (!anchor) return null;
    const parent = anchor.parentElement;
    const dropdown = buildDropdown();
    parent.replaceChild(dropdown, anchor);
    return dropdown;
  }

  const dropdown = upgradeAnchor();
  if (!dropdown) return;

  const notifCountEl = dropdown.querySelector('#notifCount');
  const notifListEl = dropdown.querySelector('#notificationsList');
  const markAllBtn = dropdown.querySelector('#markAllReadBtn');
  const clearAllBtn = dropdown.querySelector('#clearAllBtn');

  function renderNotifications(items) {
    notifListEl.innerHTML = '';
    if (!items.length) {
      notifListEl.innerHTML = '<div class="p-3 text-muted">No notifications</div>';
      notifCountEl.style.display = 'none';
      return;
    }
    items.forEach(n => {
      const a = document.createElement('a');
      a.className = 'list-group-item list-group-item-action d-flex gap-3 py-3';
      a.href = n.link || '#';
      a.dataset.id = n.id;
      a.innerHTML = `
        <div class="flex-shrink-0"> <i class="bi ${n.icon || 'bi-bell'}" style="font-size:1.2rem"></i> </div>
        <div class="lh-sm">
          <div class="d-flex justify-content-between">
            <strong>${escapeHtml(n.title)}</strong>
            <small class="text-muted">${new Date(n.created_at).toLocaleString()}</small>
          </div>
          <div class="small text-muted">${escapeHtml(n.body || '')}</div>
        </div>
      `;
      if (!n.is_read) a.classList.add('fw-bold');
      a.addEventListener('click', function (ev) {
        // mark as read
        ev.preventDefault();
        fetch('/notifications/mark-read', {
          method: 'POST',
          headers: { 'Content-Type': 'application/json' },
          body: JSON.stringify({ id: n.id }),
        }).then(() => {
          if (n.link) window.location = n.link;
          else fetchNotifications();
        });
      });
      notifListEl.appendChild(a);
    });
  }

  function fetchNotifications() {
    fetch(apiPath).then(r => r.json()).then(data => {
      if (!data.ok) return;
      renderNotifications(data.notifications || []);
      const unread = data.unread || 0;
      if (unread > 0) {
        notifCountEl.textContent = unread;
        notifCountEl.style.display = '';
      } else {
        notifCountEl.style.display = 'none';
      }
    }).catch(() => {
      // ignore
    });
  }

  function escapeHtml(s) {
    return String(s).replace(/[&<>"']/g, function (m) { return ({'&':'&amp;','<':'&lt;','>':'&gt;','"':'&quot;',"'":'&#39;'})[m]; });
  }

  markAllBtn?.addEventListener('click', function (ev) {
    ev.preventDefault();
    fetch('/notifications/mark-all-read', { method: 'POST' }).then(() => fetchNotifications());
  });

  clearAllBtn?.addEventListener('click', function (ev) {
    ev.preventDefault();
    if (!confirm('Clear all notifications?')) return;
    fetch('/notifications/clear', { method: 'POST' }).then(() => fetchNotifications());
  });

  // initial fetch and periodic refresh
  fetchNotifications();
  setInterval(fetchNotifications, 30 * 1000);
});
