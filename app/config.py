import os
from pathlib import Path

from dotenv import load_dotenv

BASE_DIR = Path(__file__).resolve().parent.parent
load_dotenv(BASE_DIR / ".env")


class Config:
    SECRET_KEY = os.environ.get("SECRET_KEY", "change-this-development-secret")
    SQLALCHEMY_DATABASE_URI = os.environ.get(
        "DATABASE_URL", f"sqlite:///{BASE_DIR / 'instance' / 'smart_invoice.db'}"
    )
    SQLALCHEMY_TRACK_MODIFICATIONS = False
    COMPANY_NAME = os.environ.get("COMPANY_NAME", "Smart Invoice Generator")
    COMPANY_ADDRESS = os.environ.get("COMPANY_ADDRESS", "123 Business Avenue, Bengaluru, Karnataka 560001")
    COMPANY_GST_NUMBER = os.environ.get("COMPANY_GST_NUMBER", "29ABCDE1234F1Z5")
