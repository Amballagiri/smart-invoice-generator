from pathlib import Path

from flask import Flask

from app.config import Config
from app.extensions import csrf, db, login_manager, mail, migrate


def create_app(test_config=None):
    app = Flask(__name__, instance_relative_config=True)
    app.config.from_object(Config)

    if test_config:
        app.config.update(test_config)

    Path(app.instance_path).mkdir(parents=True, exist_ok=True)

    # Load editable company overrides from instance/company.json (optional).
    company_file = Path(app.instance_path) / "company.json"
    if company_file.exists():
        try:
            import json

            with company_file.open("r", encoding="utf-8") as fh:
                data = json.load(fh)
            # Merge known keys into app config (no harm if extras present)
            for k, v in data.items():
                app.config[k] = v
        except Exception:
            app.logger.exception("Failed to load company overrides from instance/company.json")

    db.init_app(app)
    migrate.init_app(app, db)
    login_manager.init_app(app)
    mail.init_app(app)
    csrf.init_app(app)

    from app.models import (
        AIConversation,
        Customer,
        InventoryHistory,
        Invoice,
        InvoiceItem,
        Product,
        User,
        Notification,
    )

    from app.routes.auth import auth_bp
    from app.routes.customers import customers_bp
    from app.routes.products import products_bp
    from app.routes.invoices import invoices_bp
    from app.routes.main import main_bp
    from app.routes.ai import ai_bp

    app.register_blueprint(main_bp)
    app.register_blueprint(auth_bp)
    app.register_blueprint(customers_bp)
    app.register_blueprint(products_bp)
    app.register_blueprint(invoices_bp)
    app.register_blueprint(ai_bp)

    if app.config.get("AUTO_CREATE_DB", False):
        with app.app_context():
            db.create_all()

    return app
