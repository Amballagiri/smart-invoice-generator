(() => {
  const form = document.querySelector('#invoice-builder-form');
  if (!form) return;

  const products = JSON.parse(form.dataset.products || '{}');
  const customers = JSON.parse(form.dataset.customers || '{}');
  const rows = document.querySelector('#builder-items');
  const frameInner = document.querySelector('#preview-frame-inner');
  const zoomValue = document.querySelector('#preview-zoom-value');
  const previewColumn = document.querySelector('.builder-preview-column');
  const previewToggle = document.querySelector('[data-preview-toggle]');
  const zoomOut = document.querySelector('[data-preview-zoom-out]');
  const zoomIn = document.querySelector('[data-preview-zoom-in]');
  const fullScreenButton = document.querySelector('#preview-fullscreen');
  const scrollToPreviewButton = document.querySelector('[data-scroll-to-preview]');

  let zoomLevel = 1;
  const money = (value) => `₹${Number(value || 0).toFixed(2)}`;
  const date = (value) =>
    value
      ? new Date(`${value}T00:00:00`).toLocaleDateString(undefined, {
          day: '2-digit',
          month: 'short',
          year: 'numeric',
        })
      : '—';
  const esc = (value) =>
    String(value || '').replace(/[&<>'"]/g, (ch) =>
      ({ '&': '&amp;', '<': '&lt;', '>': '&gt;', '"': '&quot;', "'": '&#39;' }[ch])
    );

  const updateZoom = () => {
    zoomLevel = Math.max(0.6, Math.min(1.2, zoomLevel));
    if (frameInner) frameInner.style.transform = `scale(${zoomLevel})`;
    if (zoomValue) zoomValue.textContent = `${Math.round(zoomLevel * 100)}%`;
  };

  const sync = () => {
    let subtotal = 0;
    let gst = 0;
    let itemDiscount = 0;
    const previewRows = [];

    rows.querySelectorAll('.builder-item').forEach((row) => {
      const productKey = row.querySelector('.product-select').value;
      const product = products[productKey] || {};
      const quantity = Number(row.querySelector('.quantity-input').value || 0);
      const priceInput = row.querySelector('.price-input');
      const taxInput = row.querySelector('.tax-input');
      const discountInput = row.querySelector('.item-discount-input');

      if (!priceInput.value && product.price != null) {
        priceInput.value = product.price;
      }
      if (!taxInput.value && product.tax != null) {
        taxInput.value = product.tax;
      }

      const price = Number(priceInput.value || 0);
      const tax = Number(taxInput.value || 0);
      const discount = Number(discountInput?.value || 0);
      const base = quantity * price;
      const discountAmount = base * discount / 100;
      const taxable = base - discountAmount;
      const taxAmount = taxable * tax / 100;
      const total = taxable + taxAmount;

      row.querySelector('.line-total').textContent = money(total);
      subtotal += base;
      itemDiscount += discountAmount;
      gst += taxAmount;

      if (quantity || product.name) {
        previewRows.push(`
          <tr>
            <td><b>${esc(product.name || 'Item')}</b><br><small>${esc(row.querySelector('.item-description').value || product.description || '')}</small></td>
            <td>${quantity || 0}</td>
            <td>${money(price)}</td>
            <td>${tax}%</td>
            <td class="text-end">${money(total)}</td>
          </tr>
        `);
      }
    });

    const invoiceDiscount = Number(document.querySelector('#discount')?.value || 0);
    const grand = subtotal - itemDiscount + gst - invoiceDiscount;

    document.querySelector('#preview-items').innerHTML =
      previewRows.join('') || '<tr><td colspan="5" class="preview-empty">Your items will appear here</td></tr>';

    document.querySelector('#preview-subtotal').textContent = money(subtotal);
    document.querySelector('#preview-gst').textContent = money(gst);
    document.querySelector('#preview-discount').textContent = money(itemDiscount + invoiceDiscount);
    document.querySelector('#preview-grand').textContent = money(grand);
    document.querySelector('#preview-round').textContent = money(0);
    document.querySelector('#form-subtotal').textContent = money(subtotal);
    document.querySelector('#form-gst').textContent = money(gst);
    document.querySelector('#form-discount').textContent = money(itemDiscount + invoiceDiscount);
    document.querySelector('#form-round').textContent = money(0);
    document.querySelector('#form-grand').textContent = money(grand);
    document.querySelector('#preview-words').textContent = `${Math.floor(grand).toLocaleString('en-IN')} rupees only`;

    const statusField = document.querySelector('#status');
    const customerField = document.querySelector('#customer_id');
    document.querySelector('#preview-status').textContent = statusField?.selectedOptions[0]?.text.toUpperCase() || 'DRAFT';
    if (customerField) {
      const selected = customerField.selectedOptions[0];
      const previewCustomer = document.querySelector('#preview-customer');
      const previewContact = document.querySelector('#preview-customer-contact');
      const customerInfo = customers[customerField.value] || {};
      previewCustomer.textContent = selected?.text || 'Select a customer';
      const contactLines = [customerInfo.address, customerInfo.email, customerInfo.phone].filter(Boolean);
      previewContact.textContent = contactLines.length ? contactLines.join(' · ') : 'Customer details appear here';
      const summaryCustomer = document.querySelector('#summary-customer');
      const summaryContact = document.querySelector('#summary-contact');
      if (summaryCustomer) summaryCustomer.textContent = selected?.text || 'Select a customer';
      if (summaryContact) summaryContact.textContent = contactLines.length ? contactLines.join(' · ') : 'Customer details appear here';
    }
    document.querySelector('#preview-invoice-date').textContent = date(document.querySelector('#invoice_date')?.value);
    document.querySelector('#preview-due-date').textContent = date(document.querySelector('#due_date')?.value);
    document.querySelector('#preview-notes').textContent = document.querySelector('#notes')?.value || '—';
    document.querySelector('#preview-terms').textContent = document.querySelector('#terms')?.value || '—';
    document.querySelector('#a4-preview').dataset.template = document.querySelector('#template_name')?.value || 'Modern Blue';
  };

  const renumber = () => {
    rows.querySelectorAll('.builder-item').forEach((row, index) => {
      row.querySelectorAll('select, input').forEach((input) => {
        if (!input.name) return;
        input.name = input.name.replace(/items-\d+-/, `items-${index}-`);
        if (input.id) {
          input.id = input.id.replace(/items-\d+-/, `items-${index}-`);
        }
      });
    });
  };

  document.querySelector('#add-builder-item')?.addEventListener('click', () => {
    const prototypeRow = rows.querySelector('.builder-item');
    if (!prototypeRow) return;
    const row = prototypeRow.cloneNode(true);
    row.querySelectorAll('input').forEach((input) => (input.value = ''));
    row.querySelector('.product-select').value = '0';
    rows.append(row);
    renumber();
    sync();
  });

  rows.addEventListener('click', (event) => {
    const button = event.target.closest('.remove-builder-item');
    if (!button) return;
    const row = button.closest('.builder-item');
    if (!row) return;

    if (rows.children.length > 1) {
      row.remove();
    } else {
      row.querySelectorAll('input').forEach((input) => (input.value = ''));
      row.querySelector('.line-total').textContent = money(0);
    }

    renumber();
    sync();
  });

  zoomOut?.addEventListener('click', () => {
    zoomLevel -= 0.1;
    updateZoom();
  });

  zoomIn?.addEventListener('click', () => {
    zoomLevel += 0.1;
    updateZoom();
  });

  fullScreenButton?.addEventListener('click', () => {
    const target = document.querySelector('.preview-frame');
    if (!target) return;
    if (target.requestFullscreen) {
      target.requestFullscreen();
    }
  });

  scrollToPreviewButton?.addEventListener('click', () => {
    const target = document.querySelector('#preview-stage');
    target?.scrollIntoView({ behavior: 'smooth', block: 'start' });
    previewColumn?.classList.remove('collapsed');
  });

  previewToggle?.addEventListener('click', () => {
    previewColumn?.classList.toggle('collapsed');
  });

  form.addEventListener('input', sync);
  form.addEventListener('change', sync);
  updateZoom();
  sync();
})();
