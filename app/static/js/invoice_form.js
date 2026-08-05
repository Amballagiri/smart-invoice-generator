(() => {
  const form = document.querySelector('#invoice-form');
  if (!form) return;
  const products = JSON.parse(form.dataset.products || '{}');
  const container = document.querySelector('#items-container');
  const addButton = document.querySelector('#add-item');
  const discount = document.querySelector('#discount');

  const money = value => `₹${Number(value || 0).toFixed(2)}`;
  const updateTotals = () => {
    let subtotal = 0;
    let taxTotal = 0;
    container.querySelectorAll('.invoice-item').forEach(row => {
      const product = products[row.querySelector('.product-select').value];
      const quantity = Number(row.querySelector('.quantity-input').value || 0);
      const price = product ? Number(product.price) : 0;
      const tax = product ? Number(product.tax) : 0;
      const base = quantity * price;
      const itemTax = base * tax / 100;
      row.querySelector('.unit-price').textContent = money(price);
      row.querySelector('.item-tax').textContent = `${tax.toFixed(2)}%`;
      row.querySelector('.line-total').textContent = money(base + itemTax);
      subtotal += base;
      taxTotal += itemTax;
    });
    const discountValue = Number(discount.value || 0);
    document.querySelector('#subtotal').textContent = money(subtotal);
    document.querySelector('#gst-total').textContent = money(taxTotal);
    document.querySelector('#discount-preview').textContent = money(discountValue);
    document.querySelector('#grand-total').textContent = money(subtotal + taxTotal - discountValue);
  };
  const renumberRows = () => container.querySelectorAll('.invoice-item').forEach((row, index) => {
    row.querySelectorAll('select, input').forEach(field => {
      field.name = field.name.replace(/items-\d+-/, `items-${index}-`);
      field.id = field.id.replace(/items-\d+-/, `items-${index}-`);
    });
  });
  addButton.addEventListener('click', () => {
    const row = container.querySelector('.invoice-item').cloneNode(true);
    row.querySelector('.product-select').value = '0';
    row.querySelector('.quantity-input').value = '';
    row.querySelectorAll('.invalid-feedback').forEach(error => error.remove());
    container.appendChild(row);
    renumberRows();
    updateTotals();
  });
  container.addEventListener('click', event => {
    if (!event.target.closest('.remove-item')) return;
    const row = event.target.closest('.invoice-item');
    if (container.querySelectorAll('.invoice-item').length === 1) {
      row.querySelector('.product-select').value = '0';
      row.querySelector('.quantity-input').value = '';
    } else {
      row.remove();
      renumberRows();
    }
    updateTotals();
  });
  form.addEventListener('input', updateTotals);
  form.addEventListener('change', updateTotals);
  updateTotals();
})();
