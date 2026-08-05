from pathlib import Path

from flask import Flask

from app.config import Config
from app.extensions import db, login_manager, migrate


def create_app(test_config=None):
    app = Flask(__name__, instance_relative_config=True)
    app.config.from_object(Config)
    if test_config:
        app.config.update(test_config)

    Path(app.instance_path).mkdir(parents=True, exist_ok=True)
    db.init_app(app)
    migrate.init_app(app, db)
    login_manager.init_app(app)

    from app.models import Customer, Invoice, InvoiceItem, Product, User  # noqa: F401
    from app.routes.auth import auth_bp
    from app.routes.customers import customers_bp
    from app.routes.products import products_bp
    from app.routes.invoices import invoices_bp
    from app.routes.main import main_bp

    app.register_blueprint(main_bp)
    app.register_blueprint(auth_bp)
    app.register_blueprint(customers_bp)
    app.register_blueprint(products_bp)
    app.register_blueprint(invoices_bp)
    if app.config.get("AUTO_CREATE_DB", False):
        with app.app_context():
            db.create_all()
    return app
