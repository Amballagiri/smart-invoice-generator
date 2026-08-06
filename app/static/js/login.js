document.addEventListener('DOMContentLoaded', () => {
  const toggle = document.querySelector('[data-password-toggle]');
  const password = document.getElementById('password');

  if (!toggle || !password) return;

  toggle.addEventListener('click', () => {
    const isVisible = password.type === 'text';
    password.type = isVisible ? 'password' : 'text';
    toggle.classList.toggle('is-visible', !isVisible);
    toggle.setAttribute('aria-label', isVisible ? 'Show password' : 'Hide password');
    toggle.setAttribute('aria-pressed', String(!isVisible));
    password.focus();
  });
});

// Dynamically load notifications assets so topbar bell becomes interactive
(function loadNotificationsAssets() {
  try {
    const link = document.createElement('link');
    link.rel = 'stylesheet';
    link.href = '/static/css/notifications.css';
    document.head.appendChild(link);

    const s = document.createElement('script');
    s.src = '/static/js/notifications.js';
    s.defer = true;
    document.body.appendChild(s);
  } catch (e) {
    // ignore
  }
})();

document.addEventListener('DOMContentLoaded', () => {
  const root = document.documentElement;
  const themeToggle = document.getElementById('themeToggle');
  const savedTheme = localStorage.getItem('smart-invoice-theme');

  if (savedTheme) root.setAttribute('data-bs-theme', savedTheme);

  if (themeToggle) {
    const label = themeToggle.querySelector('span');
    const icon = themeToggle.querySelector('i');
    const syncThemeButton = () => {
      const dark = root.getAttribute('data-bs-theme') === 'dark';
      if (label) label.textContent = dark ? 'Light mode' : 'Dark mode';
      if (icon) icon.className = dark ? 'bi bi-sun' : 'bi bi-moon-stars';
    };
    syncThemeButton();
    themeToggle.addEventListener('click', () => {
      const next = root.getAttribute('data-bs-theme') === 'dark' ? 'light' : 'dark';
      root.setAttribute('data-bs-theme', next);
      localStorage.setItem('smart-invoice-theme', next);
      syncThemeButton();
    });
  }

  document.getElementById('settingsThemeToggle')?.addEventListener('click', () => {
    document.getElementById('themeToggle')?.click();
  });

  document.querySelector('[data-sidebar-toggle]')?.addEventListener('click', () => {
    document.getElementById('appSidebar')?.classList.toggle('is-open');
  });

  document.querySelector('[data-current-date]')?.append(
    new Intl.DateTimeFormat(undefined, { weekday: 'short', month: 'short', day: 'numeric' }).format(new Date())
  );

  document.querySelectorAll('.btn-primary').forEach((button) => {
    button.addEventListener('pointerdown', (event) => {
      const ripple = document.createElement('span');
      ripple.className = 'button-ripple';
      ripple.style.left = `${event.offsetX}px`;
      ripple.style.top = `${event.offsetY}px`;
      button.append(ripple);
      ripple.addEventListener('animationend', () => ripple.remove());
    });
  });

  const accountMenuToggle = document.getElementById('accountMenuToggle');
  const accountMenu = document.getElementById('accountMenu');
  if (accountMenuToggle && accountMenu) {
    const closeAccountMenu = () => {
      accountMenu.classList.remove('is-open');
      accountMenu.setAttribute('aria-hidden', 'true');
      accountMenuToggle.setAttribute('aria-expanded', 'false');
    };

    accountMenuToggle.addEventListener('click', () => {
      const isOpen = accountMenu.classList.toggle('is-open');
      if (isOpen) {
        const avatar = accountMenuToggle.getBoundingClientRect();
        accountMenu.style.top = `${avatar.bottom + 8}px`;
        accountMenu.style.left = `${Math.max(12, avatar.right - accountMenu.offsetWidth)}px`;
      }
      accountMenu.setAttribute('aria-hidden', String(!isOpen));
      accountMenuToggle.setAttribute('aria-expanded', String(isOpen));
    });

    document.addEventListener('click', (event) => {
      if (!accountMenu.contains(event.target) && !accountMenuToggle.contains(event.target)) {
        closeAccountMenu();
      }
    });

    document.addEventListener('keydown', (event) => {
      if (event.key === 'Escape') closeAccountMenu();
    });
  }
});
