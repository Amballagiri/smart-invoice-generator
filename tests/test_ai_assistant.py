from datetime import datetime, timedelta, timezone
from unittest.mock import MagicMock, patch
import pytest

from app.extensions import db
from app.models.ai_conversation import AIConversation
from app.models.user import User
from app.services.ai_service import AssistantError, InvoiceAssistant


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


def test_chat_automatically_clears_previous_days_history(app, client):
    with app.app_context():
        user = _user("daily_history", "daily_history@example.com")
        old_entry = AIConversation(
            user_id=user.id,
            question="Yesterday's question",
            answer="Yesterday's answer",
            created_at=datetime.now(timezone.utc) - timedelta(days=1),
        )
        today_entry = AIConversation(
            user_id=user.id,
            question="Today's question",
            answer="Today's answer",
            created_at=datetime.now(timezone.utc),
        )
        db.session.add_all((old_entry, today_entry))
        db.session.commit()
        user_id = user.id

    _login(client, type("LoggedInUser", (), {"id": user_id})())
    response = client.get("/ai-assistant/")

    assert response.status_code == 200
    with app.app_context():
        remaining = AIConversation.query.filter_by(user_id=user_id).all()
        assert [entry.question for entry in remaining] == ["Today's question"]


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


def test_answer_direct_response(app):
    with app.app_context():
        user = _user("answer_user", "answer_user@example.com")
        assistant = InvoiceAssistant(user)

        mock_message = MagicMock()
        mock_message.content = "Hello! How can I help you with your invoices today?"
        mock_message.tool_calls = None

        mock_choice = MagicMock()
        mock_choice.message = mock_message

        mock_response = MagicMock()
        mock_response.choices = [mock_choice]

        with patch("openai.OpenAI") as mock_openai_cls:
            mock_client = MagicMock()
            mock_client.chat.completions.create.return_value = mock_response
            mock_openai_cls.return_value = mock_client

            answer = assistant.answer("Hello")
            assert answer == "Hello! How can I help you with your invoices today?"

            # Check conversation was saved
            saved = AIConversation.query.filter_by(user_id=user.id).first()
            assert saved is not None
            assert saved.question == "Hello"
            assert saved.answer == "Hello! How can I help you with your invoices today?"


def test_answer_with_tool_call(app):
    with app.app_context():
        user = _user("tool_user", "tool_user@example.com")
        assistant = InvoiceAssistant(user)

        # Tool call response in first round
        mock_tool_call = MagicMock()
        mock_tool_call.id = "call_123"
        mock_tool_call.function.name = "get_business_snapshot"
        mock_tool_call.function.arguments = "{}"

        mock_tool_message = MagicMock()
        mock_tool_message.content = None
        mock_tool_message.tool_calls = [mock_tool_call]

        mock_choice_1 = MagicMock()
        mock_choice_1.message = mock_tool_message
        mock_resp_1 = MagicMock(choices=[mock_choice_1])

        # Final answer response in second round
        mock_final_message = MagicMock()
        mock_final_message.content = "You have 0 customers and ₹0 revenue this month."
        mock_final_message.tool_calls = None

        mock_choice_2 = MagicMock()
        mock_choice_2.message = mock_final_message
        mock_resp_2 = MagicMock(choices=[mock_choice_2])

        with patch("openai.OpenAI") as mock_openai_cls:
            mock_client = MagicMock()
            mock_client.chat.completions.create.side_effect = [mock_resp_1, mock_resp_2]
            mock_openai_cls.return_value = mock_client

            answer = assistant.answer("What is my business snapshot?")
            assert "₹0 revenue" in answer
            assert mock_client.chat.completions.create.call_count == 2


def test_answer_validation_errors(app):
    with app.app_context():
        user = _user("val_user", "val_user@example.com")
        assistant = InvoiceAssistant(user)

        with pytest.raises(AssistantError, match="Please enter a message"):
            assistant.answer("")

        with pytest.raises(AssistantError, match="under 2,000 characters"):
            assistant.answer("x" * 2001)


def test_answer_fallback_when_tools_unsupported(app):
    with app.app_context():
        import openai
        user = _user("fallback_user", "fallback_user@example.com")
        assistant = InvoiceAssistant(user)

        mock_message = MagicMock()
        mock_message.content = "Fallback plain response"
        mock_message.tool_calls = None
        mock_response = MagicMock(choices=[MagicMock(message=mock_message)])

        with patch("openai.OpenAI") as mock_openai_cls:
            mock_client = MagicMock()
            bad_request_err = openai.BadRequestError(
                message="tools are not supported by this model",
                response=MagicMock(status_code=400, headers={}),
                body={"error": {"message": "tools are not supported by this model"}}
            )
            mock_client.chat.completions.create.side_effect = [bad_request_err, mock_response]
            mock_openai_cls.return_value = mock_client

            answer = assistant.answer("Hello")
            assert answer == "Fallback plain response"
            assert mock_client.chat.completions.create.call_count == 2
