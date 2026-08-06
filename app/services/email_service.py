from flask_mail import Message

from app.extensions import mail
from app.services.pdf_service import generate_invoice_pdf


def send_invoice_email(invoice, company):
    """
    Generate invoice PDF and email it to the customer.
    """

    pdf = generate_invoice_pdf(invoice, company)

    msg = Message(
        subject=f"Invoice {invoice.invoice_number}",
        recipients=[invoice.customer.email],
    )

    msg.body = f"""
Hello {invoice.customer.name},

Thank you for your purchase.

Please find your invoice attached.

Invoice Number : {invoice.invoice_number}
Total Amount : ₹{invoice.grand_total}

Regards,
Smart Invoice Generator
"""

    pdf.seek(0)

    msg.attach(
        filename=f"{invoice.invoice_number}.pdf",
        content_type="application/pdf",
        data=pdf.read(),
    )

    mail.send(msg)