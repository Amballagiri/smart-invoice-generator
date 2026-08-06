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

    SQLALCHEMY_DATABASE_URI = os.environ.get(
        "DATABASE_URL",
        f"sqlite:///{BASE_DIR / 'instance' / 'smart_invoice.db'}"
    )

    SQLALCHEMY_TRACK_MODIFICATIONS = False
    MAX_CONTENT_LENGTH = 2 * 1024 * 1024
    OPENAI_API_KEY = os.environ.get("OPENAI_API_KEY")
    OPENAI_MODEL = os.environ.get("OPENAI_MODEL", "gpt-5")

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
