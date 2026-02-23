from dotenv import load_dotenv
load_dotenv()

from agent import get_response

phone = "5548999990000"
escalado = False

print("=== Teste do Agente de IA ===")
print("Digite 'sair' para encerrar\n")

while True:
    msg = input("Você: ").strip()
    if msg.lower() == "sair":
        break

    if escalado:
        print("Bot: [aguardando atendente humano — bot pausado]\n")
        continue

    result = get_response(phone_number=phone, user_message=msg)
    print(f"Bot: {result['reply']}\n")

    if result["escalate"]:
        print(">>> [ESCALOU PARA ATENDENTE HUMANO — bot pausado] <<<\n")
        escalado = True