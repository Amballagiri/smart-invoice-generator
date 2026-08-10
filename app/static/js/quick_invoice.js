(() => {
  const form = document.querySelector('#quick-invoice-form');
  if (!form) return;

  const products = JSON.parse(form.dataset.products || '{}');
  const customers = JSON.parse(form.dataset.customers || '{}');
  const rows = document.querySelector('#quick-items');
  const money = (value) => `₹${Number(value || 0).toFixed(2)}`;

  // ---- Customer datalist + auto-fill ----
  const customerName = document.querySelector('#customer_name');
  const customerPhone = document.querySelector('#customer_phone');
  const customerEmail = document.querySelector('#customer_email');
  const datalist = document.querySelector('#customer-datalist');

  if (datalist) {
    const seen = new Set();
    const options = [];
    for (const [id, c] of Object.entries(customers || {})) {
      const label = c.name || '';
      if (label && !seen.has(label)) {
        seen.add(label);
        options.push(`<option value="${label.replace(/"/g, '&quot;')}"></option>`);
      }
    }
    for (const [id, c] of Object.entries(customers || {})) {
      const phone = c.phone || '';
      if (phone && !seen.has(phone)) {
        seen.add(phone);
        options.push(`<option value="${phone.replace(/"/g, '&quot;')}"></option>`);
      }
    }
    datalist.innerHTML = options.join('');
  }

  const applyCustomerAutofill = () => {
    const value = (customerName?.value || '').trim().toLowerCase();
    if (!value) return;
    for (const c of Object.values(customers || {})) {
      if ((c.name || '').toLowerCase() === value || (c.phone || '').toLowerCase() === value) {
        if (customerPhone && !customerPhone.value) customerPhone.value = c.phone || '';
        if (customerEmail && !customerEmail.value) customerEmail.value = c.email || '';
        break;
      }
    }
  };
  customerName?.addEventListener('change', applyCustomerAutofill);

  // ---- Product search filter ----
  const productFilter = document.querySelector('#product-filter');
  const applyProductFilter = () => {
    const q = (productFilter?.value || '').trim().toLowerCase();
    rows.querySelectorAll('.product-select').forEach((select) => {
      Array.from(select.options).forEach((opt) => {
        if (!opt.value) return;
        opt.style.display = q && !opt.text.toLowerCase().includes(q) ? 'none' : '';
      });
    });
  };
  productFilter?.addEventListener('input', applyProductFilter);

  // ---- Line item sync (subtotal / GST / discount / grand total) ----
  const sync = () => {
    let subtotal = 0;
    let gst = 0;

    rows.querySelectorAll('.quick-item').forEach((row) => {
      const productKey = row.querySelector('.product-select').value;
      const product = products[productKey] || {};
      const quantity = Number(row.querySelector('.quantity-input').value || 0);
      const priceInput = row.querySelector('.price-input');
      const taxInput = row.querySelector('.tax-input');

      if (!priceInput.value && product.price != null) priceInput.value = product.price;
      if (!taxInput.value && product.tax != null) taxInput.value = product.tax;

      const price = Number(priceInput.value || 0);
      const tax = Number(taxInput.value || 0);
      const base = quantity * price;
      const taxAmount = base * tax / 100;
      row.querySelector('.line-total').textContent = money(base + taxAmount);
      subtotal += base;
      gst += taxAmount;
    });

    const invoiceDiscount = Number(document.querySelector('#discount')?.value || 0);
    const grand = subtotal + gst - invoiceDiscount;

    document.querySelector('#q-subtotal').textContent = money(subtotal);
    document.querySelector('#q-gst').textContent = money(gst);
    document.querySelector('#q-discount').textContent = money(invoiceDiscount);
    document.querySelector('#q-round').textContent = money(0);
    document.querySelector('#q-grand').textContent = money(grand);
  };

  const renumber = () => {
    rows.querySelectorAll('.quick-item').forEach((row, index) => {
      row.querySelectorAll('select, input').forEach((input) => {
        if (!input.name) return;
        input.name = input.name.replace(/items-\d+-/, `items-${index}-`);
        if (input.id) input.id = input.id.replace(/items-\d+-/, `items-${index}-`);
      });
    });
  };

  const addRow = () => {
    const proto = rows.querySelector('.quick-item');
    if (!proto) return;
    const row = proto.cloneNode(true);
    row.querySelectorAll('input').forEach((input) => (input.value = ''));
    const sel = row.querySelector('.product-select');
    sel.value = '0';
    row.querySelector('.line-total').textContent = money(0);
    rows.append(row);
    renumber();
    applyProductFilter();
    sync();
  };

  document.querySelector('#add-quick-item')?.addEventListener('click', addRow);

  rows.addEventListener('click', (event) => {
    const button = event.target.closest('.remove-quick-item');
    if (!button) return;
    const row = button.closest('.quick-item');
    if (!row) return;
    if (rows.children.length > 1) {
      row.remove();
    } else {
      row.querySelectorAll('input').forEach((input) => (input.value = ''));
      row.querySelector('.product-select').value = '0';
      row.querySelector('.line-total').textContent = money(0);
    }
    renumber();
    applyProductFilter();
    sync();
  });

  form.addEventListener('input', sync);
  form.addEventListener('change', sync);

  // ---- Quick-add product ----
  const modalEl = document.querySelector('#quickProductModal');
  const quickProductForm = document.querySelector('#quick-product-form');
  const addProductBtn = document.querySelector('#quick-add-product-btn');

  addProductBtn?.addEventListener('click', () => {
    if (typeof bootstrap !== 'undefined' && modalEl) {
      bootstrap.Modal.getOrCreateInstance(modalEl).show();
    }
  });

  quickProductForm?.addEventListener('submit', async (event) => {
    event.preventDefault();
    const body = new FormData(quickProductForm);
    const btn = quickProductForm.querySelector('button[type="submit"]');
    btn.disabled = true;
    try {
      const res = await fetch('/products/quick-add', { method: 'POST', body });
      const data = await res.json();
      if (!res.ok || !data.ok) throw new Error(data.error || 'Could not add product.');
      if (products[data.id]) {
        products[data.id] = { price: data.price, tax: data.tax, name: data.name, description: '' };
      } else {
        products[data.id] = { price: data.price, tax: data.tax, name: data.name, description: '' };
      }
      rows.querySelectorAll('.product-select').forEach((select) => {
        select.appendChild(new Option(`${data.name} (${data.sku})`, data.id));
      });
      quickProductForm.reset();
      if (typeof bootstrap !== 'undefined' && modalEl) bootstrap.Modal.getOrCreateInstance(modalEl).hide();
      sync();
    } catch (error) {
      alert(error.message);
    } finally {
      btn.disabled = false;
    }
  });

  sync();
})();
