from app.extensions import db
from app.models.inventory_history import InventoryHistory


def reduce_stock(invoice):
    """
    Reduce product stock and create inventory history.
    This function is safe to call only once per invoice.
    """

    if invoice.stock_finalized:
        return

    for item in invoice.items:

        product = item.product

        if int(product.current_stock) < int(item.quantity):
            raise ValueError(
                f"Not enough stock for {product.name}"
            )

        product.current_stock = int(product.current_stock) - int(item.quantity)

        history = InventoryHistory(
            product=product,
            user_id=invoice.created_by_id,
            invoice=invoice,
            quantity_change=-float(item.quantity),
            stock_after=float(product.current_stock),
            reason=f"Invoice {invoice.invoice_number}",
        )

        db.session.add(history)

    invoice.stock_finalized = True