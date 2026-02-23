import os
import requests
import logging

logger = logging.getLogger(__name__)

WHATSAPP_API_URL = "https://graph.facebook.com/v20.0"


def send_text_message(to: str, text: str) -> bool:
    """
    Envia uma mensagem de texto via WhatsApp Cloud API.

    Args:
        to: Número do destinatário no formato internacional sem '+' (ex: '5548999001234')
        text: Texto da mensagem

    Returns:
        True se enviado com sucesso, False caso contrário
    """
    phone_number_id = os.environ["WHATSAPP_PHONE_NUMBER_ID"]
    access_token = os.environ["WHATSAPP_ACCESS_TOKEN"]

    url = f"{WHATSAPP_API_URL}/{phone_number_id}/messages"

    payload = {
        "messaging_product": "whatsapp",
        "recipient_type": "individual",
        "to": to,
        "type": "text",
        "text": {"preview_url": False, "body": text}
    }

    headers = {
        "Authorization": f"Bearer {access_token}",
        "Content-Type": "application/json"
    }

    try:
        response = requests.post(url, json=payload, headers=headers, timeout=10)
        response.raise_for_status()
        logger.info(f"Mensagem enviada para {to}")
        return True
    except requests.exceptions.RequestException as e:
        logger.error(f"Erro ao enviar mensagem para {to}: {e}")
        if hasattr(e, 'response') and e.response is not None:
            logger.error(f"Resposta da API: {e.response.text}")
        return False


def send_escalation_notification(to: str, reply_message: str) -> bool:
    """
    Envia a mensagem de escalonamento para o cliente e alerta
    a equipe interna (pode ser adaptado para notificar um grupo ou CRM).
    """
    success = send_text_message(to, reply_message)

    internal_number = os.environ.get("WHATSAPP_ATENDENTE_NUMBER")
    if internal_number:
        alert = f"🔔 *Novo cliente aguardando atendimento humano!*\nNúmero: +{to}"
        send_text_message(internal_number, alert)

    return success


def mark_as_read(message_id: str) -> None:
    phone_number_id = os.environ["WHATSAPP_PHONE_NUMBER_ID"]
    access_token = os.environ["WHATSAPP_ACCESS_TOKEN"]
    url = f"{WHATSAPP_API_URL}/{phone_number_id}/messages"

    payload = {
        "messaging_product": "whatsapp",
        "status": "read",
        "message_id": message_id
    }

    headers = {
        "Authorization": f"Bearer {access_token}",
        "Content-Type": "application/json"
    }

    try:
        requests.post(url, json=payload, headers=headers, timeout=5)
    except Exception as e:
        logger.warning(f"Não foi possível marcar mensagem como lida: {e}")


def parse_incoming_message(data: dict) -> dict | None:
    """
    Extrai as informações relevantes de um webhook recebido da Meta.

    Returns:
        {
            "from": str,        # número do remetente
            "message_id": str,  # ID da mensagem
            "text": str,        # conteúdo da mensagem (None se não for texto)
            "type": str         # tipo: text, image, audio, etc.
        }
        ou None se não for uma mensagem válida
    """
    try:
        entry = data["entry"][0]
        changes = entry["changes"][0]
        value = changes["value"]

        if "messages" not in value:
            return None

        message = value["messages"][0]
        sender = message["from"]
        msg_id = message["id"]
        msg_type = message["type"]

        text = None
        if msg_type == "text":
            text = message["text"]["body"]
        elif msg_type == "interactive":
            if message["interactive"]["type"] == "button_reply":
                text = message["interactive"]["button_reply"]["title"]

        return {
            "from": sender,
            "message_id": msg_id,
            "text": text,
            "type": msg_type
        }

    except (KeyError, IndexError, TypeError) as e:
        logger.warning(f"Não foi possível parsear mensagem: {e}")
        return None
        