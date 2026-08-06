document.addEventListener('DOMContentLoaded', function () {
  const searchInput = document.getElementById('customerSearchInput');
  const searchForm = document.getElementById('customerSearchForm');
  const filterSelect = document.getElementById('customerFilter');
  const sortSelect = document.getElementById('customerSort');
  const rows = document.querySelectorAll('.customer-row');
  const cards = document.querySelectorAll('.customer-card');

  function applyTableFilter() {
    const filter = filterSelect.value;
    rows.forEach(row => {
      const email = row.dataset.email.trim();
      const phone = row.dataset.phone.trim();
      let visible = true;

      if (filter === 'email') visible = email !== '';
      if (filter === 'phone') visible = phone !== '';

      row.style.display = visible ? '' : 'none';
    });
  }

  filterSelect?.addEventListener('change', applyTableFilter);

  function applySearch() {
    const query = searchInput.value.trim().toLowerCase();
    rows.forEach(row => {
      const name = row.dataset.name;
      const email = row.dataset.email;
      const phone = row.dataset.phone;
      const company = row.dataset.company;
      const match = [name, email, phone, company].some(value => value.includes(query));
      row.style.display = match ? '' : 'none';
    });
  }

  searchInput?.addEventListener('input', function () {
    if (!searchInput.value) {
      rows.forEach(row => row.style.display = '');
      return;
    }
    applySearch();
  });

  sortSelect?.addEventListener('change', function () {
    const tableBody = document.getElementById('customerTableBody');
    if (!tableBody) return;
    const sortedRows = Array.from(rows).sort((a, b) => {
      const key = sortSelect.value;
      let aValue = a.dataset[key] || '';
      let bValue = b.dataset[key] || '';
      return aValue.localeCompare(bValue, undefined, {numeric: true, sensitivity: 'base'});
    });
    sortedRows.forEach(row => tableBody.appendChild(row));
  });

  searchForm?.addEventListener('submit', function (event) {
    if (!searchInput.value.trim()) {
      event.preventDefault();
      return;
    }
  });
});