import json
import os
import logging
from groq import Groq

logger = logging.getLogger(__name__)

def _load_knowledge_base() -> str:
    kb_path = os.path.join(os.path.dirname(__file__), "knowledge_base.json")
    with open(kb_path, "r", encoding="utf-8") as f:
        data = json.load(f)
    return json.dumps(data, ensure_ascii=False, indent=2)

KNOWLEDGE_BASE = _load_knowledge_base()

SYSTEM_PROMPT = f"""
Você é um assistente virtual simpático e prestativo de uma farmácia chamada "Farmácia Santa Luzia - Km60".
Seu papel é responder dúvidas comuns de clientes via WhatsApp de forma clara, natural e objetiva.

## Base de Conhecimento da Farmácia
Use APENAS as informações abaixo para responder. Não invente dados.
```json
{KNOWLEDGE_BASE}
```

## Regras Importantes

1. **Responda de forma natural e humana**, como um atendente simpático responderia, mas de maneira breve.
   Evite listas longas desnecessárias. Seja direto mas cordial.

2. **Escopo**: Só responda perguntas relacionadas aos tópicos da base de conhecimento:
   endereço, horários, entrega, pagamento, serviços, políticas, catálogo e contato.

3. **Fora do escopo / Solicitação de atendente humano**: Se a pergunta não puder ser respondida
   com as informações disponíveis, OU se o cliente pedir para falar com um atendente, responda
   APENAS com este JSON — sem nenhum texto antes ou depois, sem explicações:
   {{
     "escalate": true,
     "message": "<mensagem curta informando que um atendente irá ajudar>"
   }}
   Não responda nada além desse JSON. Não explique o motivo. Não faça perguntas antes de escalar.

4. **Dentro do escopo**: Responda em texto simples, natural, sem JSON.

5. **Emojis**: Não use emojis em nenhuma hipótese.

6. **Saudações**: Se o cliente apenas mandar "oi", "olá" ou similar, apresente-se brevemente
   e pergunte como pode ajudar. Não liste todos os serviços de uma vez.

7. **Perguntas sobre produtos específicos** — qualquer pergunta sobre disponibilidade em estoque,
   preço ou características de um medicamento ou produto específico está fora do escopo.
   Nunca confirme ou negue se um produto está disponível. Escale para atendente.

8. **Nunca mencione** que você é uma IA ou que usa inteligência artificial, a menos que
   o cliente pergunte diretamente.

9. **Horário de almoço**: A farmácia FECHA das 12h às 13h30. Se perguntarem se funciona no meio-dia ou durante o almoço, deixe claro que não, pois a loja fecha nesse período.

10. **Formatos de mídia**: Se o cliente perguntar se pode enviar áudio, imagem,
    documento, vídeo ou qualquer formato que não seja texto, escale para atendente.
    O atendente humano consegue receber e processar esses formatos.
"""

_conversation_history: dict[str, list[dict]] = {}
MAX_HISTORY_MESSAGES = 10

def get_response(phone_number: str, user_message: str) -> dict:
    """
    Processa a mensagem do usuário e retorna a resposta do agente.

    Returns:
        {
            "reply": str,        # texto a ser enviado ao cliente
            "escalate": bool     # True se deve escalar para atendente humano
        }
    """
    client = Groq(api_key=os.environ["GROQ_API_KEY"])

    if phone_number not in _conversation_history:
        _conversation_history[phone_number] = []

    history = _conversation_history[phone_number]

    history.append({"role": "user", "content": user_message})

    if len(history) > MAX_HISTORY_MESSAGES:
        history = history[-MAX_HISTORY_MESSAGES:]
        _conversation_history[phone_number] = history

    try:
        completion = client.chat.completions.create(
            model="llama-3.3-70b-versatile",
            messages=[
                {"role": "system", "content": SYSTEM_PROMPT},
                *history
            ],
            temperature=0.4,
            max_tokens=512,
        )

        raw_response = completion.choices[0].message.content.strip()
        logger.debug(f"LLM raw response: {raw_response}")

        if '"escalate": true' in raw_response:
            try:
                start = raw_response.index("{")
                end = raw_response.rindex("}") + 1
                parsed = json.loads(raw_response[start:end])
                if parsed.get("escalate"):
                    _conversation_history[phone_number].pop()
                    return {
                            "reply": parsed.get("message", "Um momento! Vou chamar um atendente para te ajudar melhor."),
                            "escalate": True
                        }
            except json.JSONDecodeError:
                pass

        history.append({"role": "assistant", "content": raw_response})
        _conversation_history[phone_number] = history

        return {"reply": raw_response, "escalate": False}

    except Exception as e:
        logger.error(f"Erro ao chamar LLM: {e}")
        return {
            "reply": "Desculpe, tive uma dificuldade técnica. Um atendente irá te responder em breve.",
            "escalate": True
        }


def clear_history(phone_number: str):
    """Limpa o histórico de conversa de um cliente."""
    _conversation_history.pop(phone_number, None)
    