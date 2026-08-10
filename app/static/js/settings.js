const ACCENT_STORAGE_KEY = 'smart-invoice-accent';
const FONT_STORAGE_KEY = 'smart-invoice-font-size';
const ACCENT_VARS = ['--brand', '--primary'];
const FONT_SCALES = { small: '87%', medium: '100%', large: '112%' };

const applyAccent = (hex) => {
  ACCENT_VARS.forEach((name) => document.documentElement.style.setProperty(name, hex));
};

const applyFontSize = (size) => {
  const scale = FONT_SCALES[size] || FONT_SCALES.medium;
  document.documentElement.style.setProperty('--app-font-scale', scale);
};

document.addEventListener('DOMContentLoaded', () => {
  const accentInput = document.getElementById('accentColor');
  const fontSizeSelect = document.getElementById('fontSize');

  const savedAccent = localStorage.getItem(ACCENT_STORAGE_KEY);
  if (savedAccent) {
    if (accentInput) accentInput.value = savedAccent;
    applyAccent(savedAccent);
  }

  const savedFont = localStorage.getItem(FONT_STORAGE_KEY);
  if (savedFont) {
    if (fontSizeSelect) fontSizeSelect.value = savedFont;
    applyFontSize(savedFont);
  }

  if (accentInput) {
    accentInput.addEventListener('input', () => {
      applyAccent(accentInput.value);
      localStorage.setItem(ACCENT_STORAGE_KEY, accentInput.value);
    });
  }

  if (fontSizeSelect) {
    fontSizeSelect.addEventListener('change', () => {
      applyFontSize(fontSizeSelect.value);
      localStorage.setItem(FONT_STORAGE_KEY, fontSizeSelect.value);
    });
  }

  document.querySelectorAll('.notification-toggle input').forEach((toggle) => {
    const storageKey = `smart-invoice-${toggle.id}`;
    const savedValue = localStorage.getItem(storageKey);
    if (savedValue !== null) toggle.checked = savedValue === 'true';
    toggle.addEventListener('change', () => localStorage.setItem(storageKey, String(toggle.checked)));
  });
});
