from pathlib import Path

from flask import current_app


def get_company_config(user):
    """Build the company dict used by PDF/email, preferring the user's shop profile.

    Falls back to the existing global app config so users without a completed
    shop profile still get usable invoice details.
    """
    profile = getattr(user, "shop_profile", None)

    name = None
    address = None
    phone = None
    email = None
    gst_number = None
    logo = None

    if profile is not None:
        name = profile.shop_name or None
        address = profile.address or None
        phone = profile.phone or None
        email = profile.email or None
        gst_number = profile.gst_number or None
        logo = _resolve_logo_path(profile.logo)

    return {
        "name": name or current_app.config.get("COMPANY_NAME", "Smart Invoice Generator"),
        "address": address or current_app.config.get("COMPANY_ADDRESS", ""),
        "gst_number": gst_number or current_app.config.get("COMPANY_GST_NUMBER", ""),
        "email": email or current_app.config.get("COMPANY_EMAIL"),
        "phone": phone or current_app.config.get("COMPANY_PHONE"),
        "logo": logo,
    }


def _resolve_logo_path(logo):
    """Return the absolute filesystem path for a stored shop logo.

    ``ShopProfile.logo`` is stored as a path relative to the static folder
    (e.g. ``uploads/logos/abc.webp``). The PDF engine needs a real filesystem
    path, so it is resolved here. Returns ``None`` when no logo is set or the
    file is missing.
    """
    if not logo:
        return None
    candidate = Path(current_app.static_folder) / logo
    if candidate.is_file():
        return str(candidate)
    return None
