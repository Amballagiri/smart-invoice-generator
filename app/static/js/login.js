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

  const ACCENT_STORAGE_KEY = 'smart-invoice-accent';
  const FONT_STORAGE_KEY = 'smart-invoice-font-size';
  const ACCENT_VARS = ['--brand', '--primary'];
  const FONT_SCALES = { small: '87%', medium: '100%', large: '112%' };

  const savedAccent = localStorage.getItem(ACCENT_STORAGE_KEY);
  if (savedAccent) ACCENT_VARS.forEach((name) => root.style.setProperty(name, savedAccent));

  const savedFont = localStorage.getItem(FONT_STORAGE_KEY);
  if (savedFont) root.style.setProperty('--app-font-scale', FONT_SCALES[savedFont] || FONT_SCALES.medium);

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

  const appSidebar = document.getElementById('appSidebar');
  const sidebarToggle = document.querySelector('[data-sidebar-toggle]');
  const isMobileSidebar = window.matchMedia('(max-width: 991.98px)');

  document.addEventListener('click', (event) => {
    if (!isMobileSidebar.matches) return;
    if (!appSidebar || !appSidebar.classList.contains('is-open')) return;
    const clickedInside = appSidebar.contains(event.target);
    const clickedToggle = sidebarToggle && sidebarToggle.contains(event.target);
    if (!clickedInside && !clickedToggle) {
      appSidebar.classList.remove('is-open');
    }
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

  const searchInput = document.getElementById('globalSearchInput');
  const searchResults = document.getElementById('globalSearchResults');

  if (searchInput && searchResults) {
    let debounceTimer = null;
    let latestQuery = '';

    const closeSearch = () => {
      searchResults.hidden = true;
      searchResults.innerHTML = '';
    };

    const renderResults = (results) => {
      searchResults.innerHTML = '';
      if (!results.length) {
        searchResults.innerHTML = '<div class="global-search-empty">No matching results</div>';
      } else {
        results.forEach((result) => {
          const anchor = document.createElement('a');
          anchor.href = result.url;
          anchor.className = 'global-search-item';
          anchor.setAttribute('role', 'option');
          const icon = result.type === 'invoice' ? 'bi-receipt' : 'bi-person';
          anchor.innerHTML = `<i class="bi ${icon}"></i><span>${result.label}</span>`;
          searchResults.appendChild(anchor);
        });
      }
      searchResults.hidden = false;
    };

    const runSearch = async (query) => {
      if (!query) {
        closeSearch();
        return;
      }
      try {
        const response = await fetch(`/search?q=${encodeURIComponent(query)}`, { headers: { 'X-Requested-With': 'XMLHttpRequest' } });
        if (!response.ok) throw new Error('search failed');
        const data = await response.json();
        if (latestQuery !== query) return;
        renderResults(data.results || []);
      } catch (error) {
        if (latestQuery === query) {
          searchResults.innerHTML = '<div class="global-search-empty">Search unavailable</div>';
          searchResults.hidden = false;
        }
      }
    };

    searchInput.addEventListener('input', () => {
      const query = searchInput.value.trim();
      latestQuery = query;
      clearTimeout(debounceTimer);
      if (!query) {
        closeSearch();
        return;
      }
      debounceTimer = setTimeout(() => runSearch(query), 250);
    });

    searchInput.addEventListener('keydown', (event) => {
      if (event.key === 'Escape') {
        closeSearch();
        searchInput.blur();
      }
    });

    document.addEventListener('keydown', (event) => {
      if ((event.ctrlKey || event.metaKey) && event.key.toLowerCase() === 'k') {
        event.preventDefault();
        searchInput.focus();
        searchInput.select();
      }
    });

    document.addEventListener('click', (event) => {
      if (!searchInput.contains(event.target) && !searchResults.contains(event.target)) {
        closeSearch();
      }
    });
  }
});
