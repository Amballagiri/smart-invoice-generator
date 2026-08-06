from app.extensions import db
from app.models.ai_conversation import AIConversation
from app.models.user import User
from app.services.ai_service import InvoiceAssistant


def _user(username, email):
    user = User(username=username, email=email)
    user.set_password("password123")
    db.session.add(user)
    db.session.commit()
    return user


def _login(client, user):
    with client.session_transaction() as session:
        session["_user_id"] = str(user.id)
        session["_fresh"] = True


def test_chat_requires_authentication(client):
    response = client.get("/ai-assistant/")
    assert response.status_code == 302


def test_chat_shows_only_signed_in_users_history(app, client):
    with app.app_context():
        owner = _user("owner", "owner@example.com")
        owner_id = owner.id
        other = _user("other", "other@example.com")
        db.session.add_all((
            AIConversation(user_id=owner.id, question="My question", answer="My answer"),
            AIConversation(user_id=other.id, question="Private question", answer="Private answer"),
        ))
        db.session.commit()

    _login(client, type("LoggedInUser", (), {"id": owner_id})())
    response = client.get("/ai-assistant/")
    assert response.status_code == 200
    assert b"My question" in response.data
    assert b"Private question" not in response.data


def test_invoice_tool_creates_user_scoped_records(app):
    with app.app_context():
        user = _user("owner", "owner@example.com")
        result = InvoiceAssistant(user)._create_invoice(
            customer_name="Rahul",
            items=[{"name": "Laptop", "quantity": 2, "unit_price": 45000, "tax_percentage": 18}],
        )
        assert result["ok"] is True
        assert result["status"] == "Draft"
        assert result["total"] == "106200.00"
