from flask import Blueprint, jsonify, render_template, request, url_for
from flask_login import current_user, login_required

from app.models.ai_conversation import AIConversation
from app.services.ai_service import AssistantError, InvoiceAssistant
from app.services.notification_service import create_notification


ai_bp = Blueprint("ai", __name__, url_prefix="/ai-assistant")


@ai_bp.get("/")
@login_required
def chat():
    InvoiceAssistant.clear_previous_days(current_user.id)
    conversations = (
        AIConversation.query.filter_by(user_id=current_user.id)
        .order_by(AIConversation.created_at.asc(), AIConversation.id.asc())
        .limit(100)
        .all()
    )
    return render_template("ai/chat.html", conversations=conversations)


@ai_bp.post("/message")
@login_required
def message():
    payload = request.get_json(silent=True) or {}
    try:
        answer = InvoiceAssistant(current_user).answer(payload.get("message"))
    except AssistantError as exc:
        return jsonify({"ok": False, "error": str(exc)}), 400
    try:
        create_notification(
            current_user.id,
            title="AI Assistant used",
            body=(payload.get("message") or "").strip()[:160],
            icon="bi-robot",
            tone="info",
            link=url_for("ai.chat"),
        )
    except Exception:
        pass
    return jsonify({"ok": True, "answer": answer})
