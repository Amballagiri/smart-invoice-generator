"""Payment routes.

Two modes, selected by ``PAYMENT_PROVIDER``:

* ``mock`` (default) - the original secure mock flow, unchanged.
* ``razorpay`` - server-verified provider flow.

Security:
* Public pages use signed tokens, never database ids.
* The only endpoints that can mark an invoice paid are owner-only (mock) or
  provider-signature-verified (Razorpay). A QR scan, a success URL, or a
  client message can never mark an invoice paid.
* The Razorpay webhook is the sole CSRF-exempt endpoint (server-to-server).
"""

import json

from flask import (
    Blueprint,
    abort,
    current_app,
    flash,
    jsonify,
    redirect,
    render_template,
    request,
    url_for,
)
from flask_login import current_user, login_required

from app.extensions import csrf
from app.models.invoice import Invoice
from app.services.payment_service import (
    PaymentError,
    PaymentResult,
    PaymentService,
    get_payment_provider,
)


payment_bp = Blueprint("payments", __name__, url_prefix="/payments")


def _invoice_from_token_or_404(token):
    """Resolve a signed payment token to an invoice or abort with 404."""
    invoice_id = PaymentService.resolve_payment_token(token)
    if invoice_id is None:
        abort(404)
    return Invoice.query.get_or_404(invoice_id)


def _owned_invoice_or_404(invoice_id):
    """Return the invoice only when it belongs to the current user."""
    invoice = Invoice.query.get_or_404(invoice_id)
    if invoice.created_by_id != current_user.id:
        abort(403)
    return invoice


def _is_paid(invoice):
    return invoice.payment_status == "Paid" or invoice.status == "Paid"


def _provider_name():
    return (current_app.config.get("PAYMENT_PROVIDER") or "mock").lower()


@payment_bp.get("/pay/<token>")
def public_payment_page(token):
    """Read-only, token-addressed payment page for customers."""
    invoice = _invoice_from_token_or_404(token)
    if _is_paid(invoice):
        return redirect(url_for("payments.payment_success", token=token))

    provider = _provider_name()
    if provider == "razorpay":
        # The generic UPI QR/deep links are mock-only; Razorpay Checkout
        # presents UPI (including QR) itself.
        qr_data = None
        upi_links = {}
    else:
        qr_data = PaymentService.generate_upi_qr_code(invoice)
        upi_links = PaymentService.generate_upi_deep_links(invoice)

    return render_template(
        "payments/pay_invoice.html",
        invoice=invoice,
        token=token,
        provider=provider,
        qr_data=qr_data,
        upi_links=upi_links,
    )


@payment_bp.get("/success/<token>")
def payment_success(token):
    """Read-only receipt page. Never mutates the invoice."""
    invoice = _invoice_from_token_or_404(token)
    if not _is_paid(invoice):
        return redirect(url_for("payments.public_payment_page", token=token))
    return render_template(
        "payments/payment_success.html",
        invoice=invoice,
        token=token,
        provider=_provider_name(),
    )


@payment_bp.get("/status/<token>")
def payment_status(token):
    """Minimal, read-only status payload for the token holder."""
    invoice = _invoice_from_token_or_404(token)
    return jsonify(
        {
            "invoice_number": invoice.invoice_number,
            "status": invoice.status,
            "payment_status": invoice.payment_status,
        }
    )


# --------------------------------------------------------------------------- #
# Razorpay provider flow
# --------------------------------------------------------------------------- #
@payment_bp.post("/pay/<token>/order")
def create_payment_order(token):
    """Create (or reuse) a provider order for the token's invoice.

    Returns only non-secret checkout parameters. CSRF protected.
    """
    invoice = _invoice_from_token_or_404(token)
    if _is_paid(invoice):
        return jsonify({"success": False, "error": "already_paid"}), 409

    provider = get_payment_provider()
    if provider is None:
        return jsonify({"success": False, "error": "razorpay_not_enabled"}), 400

    try:
        data = PaymentService.create_provider_order(invoice, provider)
    except PaymentError:
        return jsonify({"success": False, "error": "provider_error"}), 502

    return jsonify({"success": True, **data})


@payment_bp.post("/verify/<token>")
def verify_payment(token):
    """Verify a Checkout callback server-side and mark paid if valid.

    CSRF protected. The browser is never trusted: the signature, the order
    association, the provider status and the amount are all checked.
    """
    invoice = _invoice_from_token_or_404(token)
    payload = request.get_json(silent=True) or {}

    result, _updated = PaymentService.verify_provider_payment(
        invoice,
        order_id=payload.get("razorpay_order_id"),
        payment_id=payload.get("razorpay_payment_id"),
        signature=payload.get("razorpay_signature"),
    )

    ok = result in (PaymentResult.OK, PaymentResult.ALREADY_PAID)
    return jsonify({"success": ok, "result": result}), (200 if ok else 400)


@payment_bp.post("/webhook/razorpay")
@csrf.exempt
def razorpay_webhook():
    """Razorpay server-to-server webhook (CSRF-exempt, signature-verified)."""
    provider = get_payment_provider()
    if provider is None:
        return jsonify({"status": "disabled"}), 404

    raw_body = request.get_data(as_text=True)
    signature = request.headers.get("X-Razorpay-Signature", "")
    if not provider.verify_webhook_signature(raw_body, signature):
        return jsonify({"status": "invalid_signature"}), 400

    try:
        event = json.loads(raw_body or "{}")
    except ValueError:
        return jsonify({"status": "invalid_payload"}), 400

    event_id = request.headers.get("X-Razorpay-Event-Id")
    result = PaymentService.process_webhook_event(
        event,
        event_id=event_id,
        raw_body=raw_body,
        signature_valid=True,
    )
    return jsonify({"status": "ok", "result": result}), 200


# --------------------------------------------------------------------------- #
# Owner-only actions
# --------------------------------------------------------------------------- #
@payment_bp.get("/invoice/<int:invoice_id>/qr")
@login_required
def generate_qr(invoice_id):
    """Owner-only JSON QR code for an invoice."""
    invoice = _owned_invoice_or_404(invoice_id)

    qr_data = PaymentService.generate_upi_qr_code(invoice)
    if not qr_data:
        return jsonify({"success": False, "error": "Failed to generate QR code"}), 500
    return jsonify({"success": True, **qr_data})


@payment_bp.post("/invoice/<int:invoice_id>/mark-paid")
@login_required
def mark_invoice_paid(invoice_id):
    """Owner-only, CSRF-protected mock confirmation (POST only)."""
    invoice = _owned_invoice_or_404(invoice_id)

    if not PaymentService.provider_is_mock():
        flash("Manual TEST confirmation is only available in mock mode.", "info")
        return redirect(url_for("invoices.invoice_detail", invoice_id=invoice.id))

    result, _updated = PaymentService.confirm_mock_payment(
        invoice.id, request.form.get("amount")
    )

    if result == PaymentResult.OK:
        flash(f"{invoice.invoice_number} marked as paid (TEST payment).", "success")
    elif result == PaymentResult.ALREADY_PAID:
        flash(f"{invoice.invoice_number} is already marked as paid.", "info")
    elif result == PaymentResult.AMOUNT_MISMATCH:
        flash("Payment amount does not match the invoice total.", "danger")
    else:
        flash("Unable to update the payment status.", "danger")

    return redirect(url_for("invoices.invoice_detail", invoice_id=invoice.id))
