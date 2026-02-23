# Chatbot Farmácias Santa Luzia

Chatbot inteligente que responde dúvidas de clientes via WhatsApp, com escalada automática para atendimento humano.

---

## Arquitetura

```
Cliente (WhatsApp)
        │
        ▼
Meta WhatsApp Cloud API  ──POST──▶  Flask Webhook (/webhook)
                                          │
                                          ▼
                                     agent.py
                                    (Groq LLM)
                                          │
                              ┌───────────┴───────────┐
                              ▼                       ▼
                       Responde direto         Escala para
                       ao cliente              atendente humano
```

### Stack

| Componente | Serviço                        | Custo                            |
| ---------- | ------------------------------ | -------------------------------- |
| WhatsApp   | Meta Cloud API                 | Gratuito (1000 conversas/mês)    |
| LLM / IA   | Groq API (llama-3.3-70b)       | Gratuito (rate limits generosos) |
| Servidor   | Flask                          | Gratuito (self-hosted)           |
| Hospedagem | Render / Railway / VPS própria | Gratuito (tier free)             |

---

## Estrutura

```
farmacia-bot/
├── main.py              # Servidor Flask + handler do webhook
├── agent.py             # Lógica do agente de IA (Groq)
├── whatsapp_client.py   # Cliente da Meta WhatsApp Cloud API
├── knowledge_base.json  # 📝 EDITE AQUI as informações da farmácia
├── requirements.txt
├── .env.example         # Template de variáveis de ambiente
└── README.md
```

---

## Instalação e Configuração

### 1. Clone e instale dependências

```bash
# Crie e ative um ambiente virtual
python -m venv venv
source venv/bin/activate       # Linux/macOS
venv\Scripts\activate          # Windows

# Instale as dependências
pip install -r requirements.txt
```

### 2. Configure as variáveis de ambiente

```bash
cp .env.example .env
# Edite o arquivo .env com suas credenciais
```

### 3. Personalize a base de conhecimento

Abra o arquivo **`knowledge_base.json`** e preencha com os dados reais da farmácia:

- Endereço, telefone
- Horários de funcionamento
- Cidades de entrega, frete grátis
- Formas de pagamento e chave Pix
- Serviços disponíveis
- Políticas de troca

---

## Obtendo as Credenciais

### Groq API (LLM gratuito)

1. Acesse [console.groq.com](https://console.groq.com)
2. Crie uma conta (gratuita)
3. Vá em **API Keys** → **Create API Key**
4. Cole no `.env` como `GROQ_API_KEY`

### Meta WhatsApp Cloud API

1. Acesse [developers.facebook.com](https://developers.facebook.com)
2. Crie um **App** → tipo **Business**
3. Adicione o produto **WhatsApp**
4. Em **WhatsApp → API Setup**:
   - Copie o **Phone Number ID** → `WHATSAPP_PHONE_NUMBER_ID`
   - Copie o **Temporary Access Token** → `WHATSAPP_ACCESS_TOKEN`
5. Para token permanente (produção): vá no **Business Manager → System Users → Generate Token**

---

## Configurando o Webhook

A Meta precisa de uma URL pública para enviar as mensagens. Para desenvolvimento use **ngrok**:

```bash
# Instale o ngrok: https://ngrok.com/download

# Em um terminal, inicie o servidor:
python main.py

# Em outro terminal, crie o túnel:
ngrok http 5000
```

O ngrok fornecerá uma URL pública como: `https://abc123.ngrok.io`

### Registrando o Webhook na Meta

1. No painel do seu App → **WhatsApp → Configuration**
2. Em **Webhook**, clique em **Edit**:
   - **Callback URL**: `https://abc123.ngrok.io/webhook`
   - **Verify Token**: o mesmo valor de `WHATSAPP_VERIFY_TOKEN` no seu `.env`
3. Clique em **Verify and Save**
4. Ative a subscription **messages**

---

## ▶️ Executando

```bash
# Desenvolvimento
FLASK_DEBUG=true python main.py

# Produção (com gunicorn)
pip install gunicorn
gunicorn -w 2 -b 0.0.0.0:5000 main:app
```

---

## Hospedagem (Produção)

### Render.com (Recomendado)

1. Crie conta em [render.com](https://render.com)
2. **New → Web Service** → conecte seu repositório GitHub
3. Configure:
   - **Build Command**: `pip install -r requirements.txt`
   - **Start Command**: `gunicorn -w 2 -b 0.0.0.0:$PORT main:app`
4. Em **Environment**, adicione todas as variáveis do `.env`
5. Use a URL fornecida pelo Render como Callback URL no webhook da Meta

## Exemplos de Funcionamento

| Mensagem do cliente        | Comportamento                                 |
| -------------------------- | --------------------------------------------- |
| "Oi"                       | Apresenta-se e pergunta como pode ajudar      |
| "Qual o endereço?"         | Responde com endereço da base de conhecimento |
| "Vocês abrem domingo?"     | Responde com horário de domingo               |
| "Quanto custa o Dipirona?" | Escala → atendente humano                     |
| "Quero falar com alguém"   | Escala → atendente humano                     |
| "Tem farmacêutico agora?"  | Responde baseado no horário configurado       |
| Foto/áudio/documento       | Responde que só processa texto e orienta      |

---

## Personalização Avançada

### Adicionando novos tópicos à base de conhecimento

Edite o `knowledge_base.json` livremente. O agente lê todo o JSON como contexto
e saberá responder sobre qualquer informação que você adicionar.

### Alterando o modelo LLM

Em `agent.py`, altere a linha:

```python
model="llama-3.3-70b-versatile"
```

Outros modelos gratuitos no Groq: `llama3-8b-8192` (mais rápido), `mixtral-8x7b-32768`

### Histórico de conversas persistente (produção)

Substitua o dicionário `_conversation_history` em `agent.py` por Redis:

```bash
pip install redis
```

```python
import redis
r = redis.from_url(os.environ["REDIS_URL"])
# get/set com r.get(phone) / r.set(phone, json.dumps(history))
```

Redis gratuito: [Upstash](https://upstash.com) (10.000 req/dia grátis)

---

## Checklist de Deploy

- [ ] `knowledge_base.json` preenchido com dados reais da farmácia
- [ ] `.env` configurado com todas as credenciais
- [ ] Servidor hospedado e URL pública disponível
- [ ] Webhook registrado e verificado na Meta
- [ ] Subscription `messages` ativada no webhook
- [ ] Número de WhatsApp vinculado ao app Meta testado
- [ ] `WHATSAPP_ATENDENTE_NUMBER` configurado para receber alertas de escalonamento

---

## Troubleshooting

**Webhook não verifica:**
→ Confirme que `WHATSAPP_VERIFY_TOKEN` no `.env` é igual ao digitado no painel Meta.

**Mensagens não chegam:**
→ Verifique se a subscription `messages` está marcada no webhook.

**Erro 401 da API:**
→ Token expirou. Gere um novo no painel Meta ou use System User token permanente.

**Bot não responde:**
→ Verifique os logs do servidor. Confirme que `GROQ_API_KEY` é válida.
