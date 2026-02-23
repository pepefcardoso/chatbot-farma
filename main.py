import os
import logging
from flask import Flask, request, jsonify
from dotenv import load_dotenv

import agent
import whatsapp_client as wa

load_dotenv()

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(name)s: %(message)s"
)
logger = logging.getLogger(__name__)

app = Flask(__name__)

_processed_message_ids: set[str] = set()
_escalated_numbers: set[str] = set()
MAX_PROCESSED_IDS = 500


@app.route("/webhook", methods=["GET"])
def webhook_verify():
    """
    Verificação do webhook pela Meta (passo único de configuração).
    A Meta envia um GET com challenge para confirmar que a URL é sua.
    """
    verify_token = os.environ.get("WHATSAPP_VERIFY_TOKEN", "meu_token_secreto")
    mode = request.args.get("hub.mode")
    token = request.args.get("hub.verify_token")
    challenge = request.args.get("hub.challenge")

    if mode == "subscribe" and token == verify_token:
        logger.info("Webhook verificado com sucesso pela Meta!")
        return challenge, 200

    logger.warning("Falha na verificação do webhook. Token inválido.")
    return "Forbidden", 403


@app.route("/webhook", methods=["POST"])
def webhook_receive():
    """
    Recebe mensagens do WhatsApp enviadas pelos clientes.
    """
    data = request.get_json(silent=True)
    if not data:
        return jsonify({"status": "no data"}), 400

    logger.debug(f"Payload recebido: {data}")

    if data.get("object") != "whatsapp_business_account":
        return jsonify({"status": "not whatsapp"}), 400

    message_data = wa.parse_incoming_message(data)
    if not message_data:
        return jsonify({"status": "ok"}), 200

    msg_id = message_data["message_id"]
    sender = message_data["from"]
    msg_type = message_data["type"]
    text = message_data["text"]

    if msg_id in _processed_message_ids:
        logger.info(f"Mensagem duplicada ignorada: {msg_id}")
        return jsonify({"status": "duplicate"}), 200

    _processed_message_ids.add(msg_id)
    if len(_processed_message_ids) > MAX_PROCESSED_IDS:
        _processed_message_ids.clear()

    wa.mark_as_read(msg_id)

    if msg_type not in ("text", "interactive") or not text:
        _escalated_numbers.add(sender)
        reply = "Recebi uma mensagem que não consigo processar. Um atendente irá te ajudar em breve!"
        wa.send_escalation_notification(to=sender, reply_message=reply)
        agent.clear_history(sender)
        
        return jsonify({"status": "ok"}), 200

    logger.info(f"Mensagem recebida de {sender}: {text[:80]}")

    if sender in _escalated_numbers:
        return jsonify({"status": "ok"}), 200

    result = agent.get_response(phone_number=sender, user_message=text)
    reply = result["reply"]
    should_escalate = result["escalate"]

    if should_escalate:
        _escalated_numbers.add(sender)
        wa.send_escalation_notification(to=sender, reply_message=reply)
        agent.clear_history(sender)
    else:
        wa.send_text_message(to=sender, text=reply)

    return jsonify({"status": "ok"}), 200


@app.route("/health", methods=["GET"])
def health_check():
    """Endpoint simples para verificar se o servidor está no ar."""
    return jsonify({"status": "running", "service": "Farmácia Bot"}), 200

@app.route("/retomar/<numero>", methods=["POST"])
def retomar_bot(numero):
    """Chame este endpoint para reativar o bot para um número."""
    _escalated_numbers.discard(numero)
    return jsonify({"status": "bot reativado", "numero": numero}), 200

if __name__ == "__main__":
    port = int(os.environ.get("PORT", 5000))
    debug = os.environ.get("FLASK_DEBUG", "false").lower() == "true"
    
    logger.info(f"Iniciando servidor na porta {port}...")
    app.run(host="0.0.0.0", port=port, debug=debug)
    