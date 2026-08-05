from io import BytesIO

from reportlab.lib import colors
from reportlab.lib.enums import TA_LEFT, TA_RIGHT
from reportlab.lib.pagesizes import A4
from reportlab.lib.styles import ParagraphStyle, getSampleStyleSheet
from reportlab.lib.units import mm
from reportlab.platypus import Paragraph, SimpleDocTemplate, Spacer, Table, TableStyle


def generate_invoice_pdf(invoice, company):
    """Return a polished, single-document PDF for an invoice."""
    output = BytesIO()
    document = SimpleDocTemplate(
        output,
        pagesize=A4,
        leftMargin=18 * mm,
        rightMargin=18 * mm,
        topMargin=58 * mm,
        bottomMargin=22 * mm,
        title=f"Invoice {invoice.invoice_number}",
        author=company["name"],
    )
    styles = getSampleStyleSheet()
    body = ParagraphStyle("InvoiceBody", parent=styles["BodyText"], fontName="Helvetica", fontSize=9, leading=13, textColor=colors.HexColor("#334155"))
    heading = ParagraphStyle("InvoiceHeading", parent=styles["Heading2"], fontName="Helvetica-Bold", fontSize=11, leading=14, textColor=colors.HexColor("#0F172A"))
    small_right = ParagraphStyle("SmallRight", parent=body, alignment=TA_RIGHT)
    amount_right = ParagraphStyle("AmountRight", parent=body, alignment=TA_RIGHT, fontName="Helvetica-Bold")

    story = []
    details = Table(
        [
            [Paragraph("<b>Bill to</b>", heading), Paragraph("<b>Invoice details</b>", heading)],
            [
                Paragraph(_customer_details(invoice), body),
                Paragraph(
                    f"<b>Invoice number:</b> {invoice.invoice_number}<br/>"
                    f"<b>Invoice date:</b> {invoice.invoice_date:%d %b %Y}<br/>"
                    f"<b>Due date:</b> {_format_date(invoice.due_date)}<br/>"
                    f"<b>Status:</b> {invoice.status}",
                    small_right,
                ),
            ],
        ],
        colWidths=[86 * mm, 86 * mm],
    )
    details.setStyle(TableStyle([("VALIGN", (0, 0), (-1, -1), "TOP"), ("LINEBELOW", (0, 0), (-1, 0), 0.7, colors.HexColor("#CBD5E1")), ("BOTTOMPADDING", (0, 0), (-1, 0), 7), ("TOPPADDING", (0, 1), (-1, -1), 8)]))
    story += [details, Spacer(1, 10 * mm)]

    rows = [["Product", "Qty", "Unit price", "GST", "Total"]]
    for item in invoice.items:
        rows.append([
            Paragraph(f"<b>{item.product.name}</b><br/><font size=8 color='#64748B'>{item.product.sku}</font>", body),
            Paragraph(f"{item.quantity} {item.product.unit}", small_right),
            Paragraph(_money(item.unit_price), small_right),
            Paragraph(f"{item.tax_percentage}%", small_right),
            Paragraph(_money(item.line_total), amount_right),
        ])
    table = Table(rows, colWidths=[70 * mm, 23 * mm, 29 * mm, 18 * mm, 32 * mm], repeatRows=1)
    table.setStyle(TableStyle([
        ("BACKGROUND", (0, 0), (-1, 0), colors.HexColor("#0F4C81")),
        ("TEXTCOLOR", (0, 0), (-1, 0), colors.white),
        ("FONTNAME", (0, 0), (-1, 0), "Helvetica-Bold"),
        ("FONTSIZE", (0, 0), (-1, -1), 9),
        ("ALIGN", (1, 0), (-1, -1), "RIGHT"),
        ("VALIGN", (0, 0), (-1, -1), "MIDDLE"),
        ("GRID", (0, 0), (-1, -1), 0.25, colors.HexColor("#E2E8F0")),
        ("ROWBACKGROUNDS", (0, 1), (-1, -1), [colors.white, colors.HexColor("#F8FAFC")]),
        ("TOPPADDING", (0, 0), (-1, -1), 8),
        ("BOTTOMPADDING", (0, 0), (-1, -1), 8),
        ("LEFTPADDING", (0, 0), (-1, -1), 7),
        ("RIGHTPADDING", (0, 0), (-1, -1), 7),
    ]))
    story += [table, Spacer(1, 7 * mm)]

    subtotal = invoice.grand_total - invoice.gst_total + invoice.discount
    totals = Table(
        [
            ["Subtotal", _money(subtotal)],
            ["GST", _money(invoice.gst_total)],
            ["Discount", _money(invoice.discount)],
            ["Grand total", _money(invoice.grand_total)],
        ],
        colWidths=[36 * mm, 32 * mm],
        hAlign="RIGHT",
    )
    totals.setStyle(TableStyle([
        ("ALIGN", (0, 0), (-1, -1), "RIGHT"),
        ("FONTNAME", (0, 0), (-1, -2), "Helvetica"),
        ("FONTNAME", (0, -1), (-1, -1), "Helvetica-Bold"),
        ("BACKGROUND", (0, -1), (-1, -1), colors.HexColor("#DBEAFE")),
        ("TEXTCOLOR", (0, -1), (-1, -1), colors.HexColor("#0F172A")),
        ("LINEABOVE", (0, -1), (-1, -1), 0.7, colors.HexColor("#2563EB")),
        ("TOPPADDING", (0, 0), (-1, -1), 6),
        ("BOTTOMPADDING", (0, 0), (-1, -1), 6),
    ]))
    story += [totals, Spacer(1, 10 * mm)]
    if invoice.notes:
        story += [Paragraph("<b>Notes</b>", heading), Spacer(1, 2 * mm), Paragraph(invoice.notes, body), Spacer(1, 8 * mm)]
    story.append(Paragraph("Thank you for your business.", ParagraphStyle("ThankYou", parent=body, fontName="Helvetica-Bold", fontSize=10, textColor=colors.HexColor("#0F4C81"))))
    document.build(story, onFirstPage=lambda canvas, doc: _draw_header_footer(canvas, doc, company), onLaterPages=lambda canvas, doc: _draw_header_footer(canvas, doc, company))
    output.seek(0)
    return output


def _draw_header_footer(canvas, document, company):
    width, height = A4
    canvas.saveState()
    canvas.setFillColor(colors.HexColor("#0F4C81"))
    canvas.roundRect(18 * mm, height - 42 * mm, 16 * mm, 16 * mm, 3 * mm, fill=1, stroke=0)
    canvas.setFillColor(colors.white)
    canvas.setFont("Helvetica-Bold", 15)
    canvas.drawCentredString(26 * mm, height - 36.5 * mm, "SI")
    canvas.setFillColor(colors.HexColor("#0F172A"))
    canvas.setFont("Helvetica-Bold", 16)
    canvas.drawString(40 * mm, height - 31 * mm, company["name"])
    canvas.setFillColor(colors.HexColor("#475569"))
    canvas.setFont("Helvetica", 8.5)
    address_lines = _wrap_address(company["address"])
    y = height - 36 * mm
    for line in address_lines:
        canvas.drawString(40 * mm, y, line)
        y -= 4 * mm
    canvas.drawRightString(width - 18 * mm, height - 31 * mm, f"GSTIN: {company['gst_number']}")
    canvas.setStrokeColor(colors.HexColor("#CBD5E1"))
    canvas.line(18 * mm, height - 48 * mm, width - 18 * mm, height - 48 * mm)
    canvas.setFillColor(colors.HexColor("#64748B"))
    canvas.setFont("Helvetica", 8)
    canvas.drawCentredString(width / 2, 12 * mm, f"{company['name']} | Computer generated invoice")
    canvas.restoreState()


def _customer_details(invoice):
    customer = invoice.customer
    lines = [f"<b>{customer.name}</b>"]
    for value in (customer.address, customer.city, customer.state, customer.postal_code, customer.country, customer.email, customer.phone):
        if value:
            lines.append(str(value))
    return "<br/>".join(lines)


def _format_date(value):
    return value.strftime("%d %b %Y") if value else "-"


def _money(value):
    return f"INR {value:,.2f}"


def _wrap_address(address):
    words, lines, current = address.split(), [], ""
    for word in words:
        candidate = f"{current} {word}".strip()
        if len(candidate) > 58 and current:
            lines.append(current)
            current = word
        else:
            current = candidate
    if current:
        lines.append(current)
    return lines[:2]
