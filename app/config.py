import os
from pathlib import Path

from dotenv import load_dotenv

BASE_DIR = Path(__file__).resolve().parent.parent
load_dotenv(BASE_DIR / ".env")


class Config:
    SECRET_KEY = os.environ.get(
        "SECRET_KEY",
        "change-this-development-secret"
    )

    _database_url = os.environ.get(
        "DATABASE_URL",
        f"sqlite:///{BASE_DIR / 'instance' / 'smart_invoice.db'}"
    )

    # Render exposes PostgreSQL as "postgres://", which SQLAlchemy 2.x + psycopg2
    # does not accept. Normalize to "postgresql://" while leaving SQLite/local
    # URIs untouched.
    if _database_url.startswith("postgres://"):
        _database_url = "postgresql://" + _database_url[len("postgres://"):]

    SQLALCHEMY_DATABASE_URI = _database_url

    SQLALCHEMY_TRACK_MODIFICATIONS = False
    MAX_CONTENT_LENGTH = 2 * 1024 * 1024
    AI_PROVIDER = os.environ.get("AI_PROVIDER", "openai").strip().lower()
    OPENAI_API_KEY = os.environ.get("OPENAI_API_KEY")
    OPENAI_MODEL = os.environ.get("OPENAI_MODEL", "gpt-4o-mini")
    OPENROUTER_API_KEY = os.environ.get("OPENROUTER_API_KEY")
    # Keep this to a currently available OpenRouter free model. The older
    # Gemini 2.0 experimental route has been retired by the provider.
    OPENROUTER_MODEL = os.environ.get("OPENROUTER_MODEL", "inclusionai/ling-3.0-flash-sante:free")

    # ---------------- GOOGLE OAUTH ----------------

    GOOGLE_CLIENT_ID = os.environ.get("GOOGLE_CLIENT_ID")
    GOOGLE_CLIENT_SECRET = os.environ.get("GOOGLE_CLIENT_SECRET")
    # Optional override. When unset, the callback is built from the request host.
    GOOGLE_REDIRECT_URI = os.environ.get("GOOGLE_REDIRECT_URI")

    COMPANY_NAME = os.environ.get(
        "COMPANY_NAME",
        "Smart Invoice Generator"
    )

    COMPANY_ADDRESS = os.environ.get(
        "COMPANY_ADDRESS",
        "123 Business Avenue, Bengaluru, Karnataka 560001"
    )

    COMPANY_GST_NUMBER = os.environ.get(
        "COMPANY_GST_NUMBER",
        "29ABCDE1234F1Z5"
    )

    COMPANY_EMAIL = os.environ.get("COMPANY_EMAIL")

    COMPANY_PHONE = os.environ.get("COMPANY_PHONE")

    # ---------------- PAYMENTS ----------------

    # Which payment provider to use. Defaults to the secure local mock so no
    # network calls are made until a real provider is explicitly enabled.
    PAYMENT_PROVIDER = os.environ.get("PAYMENT_PROVIDER", "mock").strip().lower()

    # Base URL of this application, used to build provider callbacks and
    # payment links. Reused by the payment layer.
    BASE_URL = os.environ.get("BASE_URL")

    # Razorpay credentials are read from the environment only. Never hardcode
    # them and never expose the key secret or webhook secret to templates.
    RAZORPAY_KEY_ID = os.environ.get("RAZORPAY_KEY_ID")
    RAZORPAY_KEY_SECRET = os.environ.get("RAZORPAY_KEY_SECRET")
    RAZORPAY_WEBHOOK_SECRET = os.environ.get("RAZORPAY_WEBHOOK_SECRET")

    # ---------------- MAIL ----------------

    MAIL_SERVER = os.environ.get("MAIL_SERVER")

    MAIL_PORT = int(os.environ.get("MAIL_PORT", 587))

    MAIL_USE_TLS = os.environ.get(
        "MAIL_USE_TLS",
        "True"
    ) == "True"

    MAIL_USERNAME = os.environ.get("MAIL_USERNAME")

    MAIL_PASSWORD = os.environ.get("MAIL_PASSWORD")

    MAIL_DEFAULT_SENDER = os.environ.get("MAIL_DEFAULT_SENDER")
