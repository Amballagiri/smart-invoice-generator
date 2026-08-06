document.addEventListener('DOMContentLoaded', () => {
  document.querySelectorAll('.notification-toggle input').forEach((toggle) => {
    const storageKey = `smart-invoice-${toggle.id}`;
    const savedValue = localStorage.getItem(storageKey);
    if (savedValue !== null) toggle.checked = savedValue === 'true';
    toggle.addEventListener('change', () => localStorage.setItem(storageKey, String(toggle.checked)));
  });
});
