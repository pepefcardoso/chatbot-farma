# 🤖 Farmácias Santa Luzia — WhatsApp Chatbot

> Chatbot inteligente para atendimento via WhatsApp com escalada automática para atendente humano, construído com Python, Flask e Groq LLM.

---

## Sumário

- [Visão Geral](#visão-geral)
- [Funcionalidades](#funcionalidades)
- [Arquitetura](#arquitetura)
- [Stack Tecnológica](#stack-tecnológica)
- [Pré-requisitos](#pré-requisitos)
- [Instalação](#instalação)
- [Configuração do Ambiente](#configuração-do-ambiente)
- [Base de Conhecimento](#base-de-conhecimento)
- [Obtendo as Credenciais](#obtendo-as-credenciais)
- [Configurando o Webhook](#configurando-o-webhook)
- [Executando o Projeto](#executando-o-projeto)
- [Estrutura de Arquivos](#estrutura-de-arquivos)
- [Fluxo de Mensagens](#fluxo-de-mensagens)
- [Lógica de Escalada](#lógica-de-escalada)
- [Endpoints da API](#endpoints-da-api)
- [Exemplos de Interação](#exemplos-de-interação)
- [Hospedagem em Produção](#hospedagem-em-produção)
- [Personalização Avançada](#personalização-avançada)
- [Troubleshooting](#troubleshooting)
- [Limitações Conhecidas](#limitações-conhecidas)
- [Roadmap](#roadmap)

---

## Visão Geral

O **Farmácias Santa Luzia Bot** é um assistente virtual para WhatsApp que responde automaticamente às dúvidas mais frequentes dos clientes — horários, endereço, serviços, formas de pagamento, política de entregas — tudo com base em uma base de conhecimento configurável em JSON.

Quando o cliente faz uma pergunta fora do escopo (como disponibilidade ou preço de um medicamento específico), o bot **escala automaticamente para um atendente humano**, pausando o bot para aquele número até que o atendimento seja retomado manualmente.

O projeto foi desenhado para ser **100% gratuito** no tier de uso moderado, utilizando a API da Meta para WhatsApp e o Groq como provedor de LLM.

---

## Funcionalidades

- **Respostas automáticas** a perguntas sobre endereço, horários, serviços, pagamento, entrega e políticas da farmácia
- **Histórico de conversa por sessão** — o bot mantém o contexto das últimas 10 mensagens de cada cliente
- **Escalada inteligente para atendente humano** — ativada automaticamente quando a pergunta está fora do escopo ou o cliente solicita atendimento humano
- **Notificação ao atendente** — ao escalar, o número do atendente configurado recebe um alerta via WhatsApp
- **Deduplicação de mensagens** — mensagens duplicadas enviadas pela Meta são ignoradas automaticamente
- **Marcação de mensagens como lidas** — o "duplo check azul" é acionado ao receber a mensagem
- **Tratamento de mídia** — áudios, imagens e documentos são recebidos e escalados para atendente humano
- **Retomada manual do bot** — endpoint HTTP para reativar o bot para um número específico após atendimento humano
- **Base de conhecimento editável** — nenhum código precisa ser alterado para atualizar informações da farmácia
- **Health check endpoint** — para monitoramento do servidor

---

## Arquitetura

```
Cliente (WhatsApp)
        │
        ▼ POST /webhook
Meta WhatsApp Cloud API
        │
        ▼
  Flask (main.py)
  ┌─────────────────────────────────┐
  │  Deduplicação de mensagens       │
  │  Verificação de escalada ativa   │
  │  Roteamento por tipo de mídia    │
  └────────────────┬────────────────┘
                   │
                   ▼
            agent.py (Groq LLM)
            ┌────────────────────────────┐
            │  Carrega base de conhecimento│
            │  Mantém histórico por número │
            │  Chama llama-3.3-70b via     │
            │  Groq API                    │
            │  Parseia resposta JSON ou    │
            │  texto livre                 │
            └──────────┬─────────────────┘
                       │
          ┌────────────┴────────────┐
          ▼                         ▼
  Responde direto             Escala para
  (send_text_message)         atendente humano
                              (send_escalation_notification)
                              + pausa o bot para o número
```

---

## Stack Tecnológica

| Componente | Tecnologia | Custo |
|---|---|---|
| Servidor Web | Flask 3.0 | Gratuito |
| LLM / IA | Groq API — `llama-3.3-70b-versatile` | Gratuito (rate limits generosos) |
| Mensageria | Meta WhatsApp Cloud API | Gratuito (1.000 conversas/mês) |
| Hospedagem | Render / Railway / VPS própria | Gratuito (tier free) |
| Histórico de sessão | Dicionário em memória (padrão) / Redis (produção) | Gratuito |

---

## Pré-requisitos

- Python 3.10 ou superior
- Conta na [Meta for Developers](https://developers.facebook.com) com um app do tipo **Business** configurado
- Conta no [Groq Console](https://console.groq.com) para obter a API Key
- Um número de WhatsApp vinculado ao app Meta (pode ser um número de teste)
- `ngrok` ou outra solução de túnel para desenvolvimento local (ou URL pública em produção)

---

## Instalação

```bash
# 1. Clone o repositório
git clone https://github.com/seu-usuario/farmacia-bot.git
cd farmacia-bot

# 2. Crie e ative um ambiente virtual
python -m venv venv

# Linux/macOS
source venv/bin/activate

# Windows
venv\Scripts\activate

# 3. Instale as dependências
pip install -r requirements.txt
```

---

## Configuração do Ambiente

```bash
# Copie o arquivo de exemplo
cp .env.example .env
```

Edite o arquivo `.env` com suas credenciais:

```env
# Chave da API Groq — obtida em console.groq.com
GROQ_API_KEY=gsk_xxxxxxxxxxxxxxxxxxxxxx

# ID do número de telefone no painel Meta (somente dígitos)
WHATSAPP_PHONE_NUMBER_ID=123456789012345

# Token de acesso da API Meta (temporário ou permanente)
WHATSAPP_ACCESS_TOKEN=EAAxxxxxxxxxxxxxxxx

# Token secreto que você escolhe para validar o webhook
WHATSAPP_VERIFY_TOKEN=meu_token_secreto_aqui_123

# Número do atendente que receberá alertas de escalada
# Formato internacional sem '+': 5548990001234
WHATSAPP_ATENDENTE_NUMBER=5548990001234

# Porta do servidor Flask
PORT=5000

# true para modo desenvolvimento (logs detalhados, reload automático)
FLASK_DEBUG=false
```

> **Segurança:** nunca commite o arquivo `.env` no repositório. Ele já está incluído no `.gitignore`.

---

## Base de Conhecimento

Toda a informação que o bot usa para responder está em `knowledge_base.json`. Edite esse arquivo para personalizar o bot para qualquer farmácia — sem alterar nenhum código Python.

### Estrutura do arquivo

```json
{
  "farmacia": {
    "nome": "Farmácias Santa Luzia",
    "endereco": "SC-390, 4948 - KM-60, Tubarão - SC",
    "telefone": "(48) 3632-6351",
    "whatsapp": "(48) 99156-5677"
  },
  "horarios": {
    "segunda_a_sexta": "08h às 12h e 13h30 às 20h",
    "sabado": "08h às 12h e 13h30 às 20h",
    "domingo": "Fechado",
    "feriados_nacionais": "Fechado",
    "e_24_horas": false,
    "fechado_almoco": "A farmácia fecha para almoço das 12h às 13h30..."
  },
  "entrega": { ... },
  "pagamento": { ... },
  "servicos": { ... },
  "politicas": { ... },
  "catalogo": { ... }
}
```

### Seções disponíveis

| Seção | O que configura |
|---|---|
| `farmacia` | Nome, endereço, telefone, WhatsApp |
| `horarios` | Horários por dia da semana, fechamento de almoço, plantão farmacêutico |
| `entrega` | Cidades atendidas, frete grátis, horário do motoboy, tempo médio |
| `pagamento` | Pix (chave e tipo), cartão de crédito/débito, dinheiro, benefícios |
| `servicos` | Injetáveis, testes rápidos, curativo, nebulização, furo de orelha, etc. |
| `politicas` | Troca de produtos, receitas de outros estados, receita digital, controle especial |
| `catalogo` | Se a farmácia possui catálogo online disponível |

O bot lê todo o JSON como contexto e responde sobre qualquer campo presente. Você pode adicionar novos campos livremente — o LLM saberá interpretá-los.

---

## Obtendo as Credenciais

### Groq API Key

1. Acesse [console.groq.com](https://console.groq.com) e crie uma conta gratuita
2. No menu lateral, vá em **API Keys** → **Create API Key**
3. Copie o valor e adicione ao `.env` como `GROQ_API_KEY`

> O plano gratuito do Groq oferece aproximadamente 14.400 requisições/dia para o modelo `llama-3.3-70b-versatile`, mais do que suficiente para uso moderado.

### Meta WhatsApp Cloud API

1. Acesse [developers.facebook.com](https://developers.facebook.com) e faça login
2. Clique em **My Apps** → **Create App**
3. Selecione o tipo **Business** e conclua o assistente
4. No painel do app, clique em **Add Product** → **WhatsApp** → **Set Up**
5. Em **WhatsApp → API Setup**:
   - Em **From**, selecione ou crie um número de teste
   - Copie o **Phone Number ID** → coloque em `WHATSAPP_PHONE_NUMBER_ID`
   - Copie o **Temporary Access Token** → coloque em `WHATSAPP_ACCESS_TOKEN`
6. Para usar em produção com token permanente:
   - Acesse o **Business Manager** → **System Users**
   - Crie um System User com permissão de **Admin**
   - Gere um token permanente vinculado ao seu app

---

## Configurando o Webhook

A Meta envia as mensagens para uma URL pública que você registra. Para desenvolvimento, use o `ngrok` para expor seu servidor local:

```bash
# Terminal 1: inicie o servidor Flask
python main.py

# Terminal 2: crie o túnel público
ngrok http 5000
```

O ngrok exibirá uma URL como `https://abc123.ngrok.io`.

### Registrando o Webhook no painel Meta

1. No painel do app → **WhatsApp → Configuration**
2. Em **Webhook**, clique em **Edit**
3. Preencha:
   - **Callback URL**: `https://abc123.ngrok.io/webhook`
   - **Verify Token**: o mesmo valor de `WHATSAPP_VERIFY_TOKEN` no seu `.env`
4. Clique em **Verify and Save**
5. Na seção **Webhook Fields**, ative a subscription **messages**

> **Atenção:** A URL do ngrok muda a cada reinicialização no plano gratuito. Para produção, use uma URL fixa (Render, Railway, VPS).

---

## Executando o Projeto

### Desenvolvimento

```bash
# Com hot-reload e logs detalhados
FLASK_DEBUG=true python main.py
```

### Testando o agente sem WhatsApp

Use o script interativo para testar o comportamento do LLM diretamente no terminal:

```bash
python test_agent.py
```

```
=== Teste do Agente de IA ===
Digite 'sair' para encerrar

Você: qual o endereço?
Bot: A farmácia fica na SC-390, 4948 - KM-60, em Tubarão - SC.

Você: vocês têm dipirona?
Bot: Um momento! Vou chamar um atendente para te ajudar melhor.
>>> [ESCALOU PARA ATENDENTE HUMANO — bot pausado] <<<
```

### Produção (com Gunicorn)

```bash
pip install gunicorn
gunicorn -w 2 -b 0.0.0.0:5000 main:app
```

---

## Estrutura de Arquivos

```
farmacia-bot/
├── main.py              # Servidor Flask: webhook GET/POST, roteamento, deduplicação
├── agent.py             # Lógica do agente: prompt, histórico, chamada ao Groq LLM
├── whatsapp_client.py   # Cliente da Meta API: envio, escalada, leitura, parse
├── knowledge_base.json  # Base de conhecimento editável — dados reais da farmácia
├── test_agent.py        # Script interativo para testar o agente no terminal
├── requirements.txt     # Dependências Python
├── .env.example         # Template de variáveis de ambiente
└── README.md
```

### Responsabilidades por arquivo

**`main.py`**
- Inicialização do Flask e carregamento das variáveis de ambiente
- `GET /webhook` — verificação do webhook pela Meta
- `POST /webhook` — recebimento e roteamento de mensagens
- Deduplicação por `message_id` (set em memória, limite de 500 IDs)
- Controle do set `_escalated_numbers` (números pausados para atendimento humano)
- `GET /health` — health check
- `POST /retomar/<numero>` — reativa o bot para um número após atendimento humano

**`agent.py`**
- Carrega `knowledge_base.json` uma vez na inicialização
- Define o `SYSTEM_PROMPT` com as regras de comportamento e a base de conhecimento embutida
- `get_response(phone_number, user_message)` — gerencia histórico e chama o Groq
- Parseia a resposta: se contiver `"escalate": true`, retorna flag de escalada; caso contrário, retorna texto livre
- Histórico limitado a 10 mensagens por número (FIFO)

**`whatsapp_client.py`**
- `send_text_message(to, text)` — envia mensagem de texto via Graph API
- `send_escalation_notification(to, reply_message)` — envia mensagem ao cliente + alerta ao atendente
- `mark_as_read(message_id)` — marca mensagem como lida (duplo check azul)
- `parse_incoming_message(data)` — extrai remetente, ID, tipo e texto do payload da Meta

---

## Fluxo de Mensagens

```
Mensagem recebida
      │
      ▼
Mensagem duplicada? ──► SIM ──► Ignorar (retorna 200)
      │
      ▼ NÃO
Marcar como lida
      │
      ▼
Tipo de mídia? (áudio/imagem/doc/vídeo)
      │
      ▼ SIM
Escalar + notificar atendente + limpar histórico
      │
      ▼ NÃO (texto ou interactive)
Número já escalado?
      │
      ▼ SIM ──► Ignorar silenciosamente (bot pausado)
      │
      ▼ NÃO
Chamar agent.get_response()
      │
      ├─► escalate: false ──► Enviar resposta ao cliente
      │
      └─► escalate: true  ──► Escalar + notificar atendente
                               + limpar histórico
                               + adicionar ao set de escalados
```

---

## Lógica de Escalada

O bot escala para atendente humano nos seguintes casos:

1. **Pergunta fora do escopo** — o LLM não encontra a resposta na base de conhecimento
2. **Pergunta sobre produto específico** — qualquer pergunta sobre disponibilidade, preço ou características de um medicamento
3. **Cliente solicita atendente** — frases como "quero falar com um humano", "me passa para o atendente"
4. **Mensagem de mídia** — áudio, imagem, documento, vídeo (o bot não processa esses formatos)
5. **Erro técnico** — falha na chamada ao Groq LLM

Ao escalar:
- O número do cliente é adicionado ao set `_escalated_numbers`
- O bot para de responder para aquele número
- O atendente configurado em `WHATSAPP_ATENDENTE_NUMBER` recebe um alerta
- O histórico de conversa do cliente é limpo

Para reativar o bot após o atendimento humano:

```bash
POST /retomar/5548999990000
```

---

## Endpoints da API

| Método | Rota | Descrição |
|---|---|---|
| `GET` | `/webhook` | Verificação do webhook pela Meta |
| `POST` | `/webhook` | Recebimento de mensagens dos clientes |
| `GET` | `/health` | Health check do servidor |
| `POST` | `/retomar/<numero>` | Reativa o bot para um número específico |

---

## Exemplos de Interação

| Mensagem do cliente | Comportamento | Tipo de resposta |
|---|---|---|
| "Oi" / "Olá" | Apresenta-se e pergunta como pode ajudar | Texto |
| "Qual o endereço?" | Retorna o endereço da base de conhecimento | Texto |
| "Vocês abrem domingo?" | Informa que está fechado aos domingos | Texto |
| "Funciona no almoço?" | Informa o fechamento das 12h às 13h30 | Texto |
| "Vocês fazem aplicação de injetável?" | Explica o serviço e a necessidade de receita | Texto |
| "Qual a chave Pix?" | Retorna o CNPJ como chave Pix | Texto |
| "Quanto custa o Dipirona?" | Escala para atendente humano | Escalada |
| "Tem paracetamol em estoque?" | Escala para atendente humano | Escalada |
| "Quero falar com alguém" | Escala para atendente humano | Escalada |
| [Envia áudio] | Responde que não processa e escala | Escalada |
| "Vocês entregam em Laguna?" | Confirma a entrega e informa condições | Texto |
| "Aceitam cartão de crédito?" | Informa parcelas e valor mínimo | Texto |

---

## Hospedagem em Produção

### Render.com (Recomendado — Gratuito)

1. Crie uma conta em [render.com](https://render.com)
2. **New → Web Service** → conecte seu repositório GitHub
3. Configure o serviço:
   - **Environment**: Python 3
   - **Build Command**: `pip install -r requirements.txt`
   - **Start Command**: `gunicorn -w 2 -b 0.0.0.0:$PORT main:app`
4. Em **Environment Variables**, adicione todas as variáveis do `.env`
5. Após o deploy, use a URL fornecida pelo Render como Callback URL no webhook da Meta

> O plano gratuito do Render pode ter cold start de ~30 segundos após inatividade. Para bots em produção, considere o plano pago ou use Railway.

### Railway

1. Acesse [railway.app](https://railway.app) e conecte o repositório
2. Configure as variáveis de ambiente
3. O Railway detecta automaticamente o Python e executa `gunicorn`

### VPS própria (nginx + gunicorn)

```nginx
server {
    listen 80;
    server_name seudominio.com.br;

    location / {
        proxy_pass http://127.0.0.1:5000;
        proxy_set_header Host $host;
        proxy_set_header X-Real-IP $remote_addr;
    }
}
```

```bash
# Inicie com supervisor ou systemd para persistência
gunicorn -w 2 -b 127.0.0.1:5000 main:app
```

---

## Personalização Avançada

### Alterando o modelo LLM

Em `agent.py`, altere a propriedade `model`:

```python
# Mais rápido, menor custo de tokens
model="llama3-8b-8192"

# Padrão atual — melhor qualidade
model="llama-3.3-70b-versatile"

# Alternativa
model="mixtral-8x7b-32768"
```

### Histórico de conversas persistente (Redis)

O histórico padrão é em memória e se perde ao reiniciar o servidor. Para produção com alta disponibilidade, use Redis:

```bash
pip install redis
```

```python
# Em agent.py, substitua o dicionário por chamadas ao Redis
import redis

r = redis.from_url(os.environ["REDIS_URL"])

def _get_history(phone: str) -> list:
    raw = r.get(f"history:{phone}")
    return json.loads(raw) if raw else []

def _set_history(phone: str, history: list):
    r.set(f"history:{phone}", json.dumps(history), ex=86400)  # TTL 24h
```

Redis gratuito: [Upstash](https://upstash.com) oferece 10.000 requisições/dia grátis.

### Múltiplas farmácias

Para suportar múltiplas unidades, parametrize o `knowledge_base.json` por número de WhatsApp:

```python
def _load_knowledge_base(phone_number_id: str) -> str:
    path = f"knowledge_bases/{phone_number_id}.json"
    # ...
```

### Adicionando respostas com botões interativos

A Meta Cloud API suporta mensagens com botões (`interactive`). Para enviar botões:

```python
payload = {
    "messaging_product": "whatsapp",
    "to": to,
    "type": "interactive",
    "interactive": {
        "type": "button",
        "body": {"text": "Como posso te ajudar?"},
        "action": {
            "buttons": [
                {"type": "reply", "reply": {"id": "horarios", "title": "Horários"}},
                {"type": "reply", "reply": {"id": "entrega", "title": "Entrega"}},
                {"type": "reply", "reply": {"id": "servicos", "title": "Serviços"}},
            ]
        }
    }
}
```

---

## Troubleshooting

**Webhook não verifica (erro 403)**
→ Confira que `WHATSAPP_VERIFY_TOKEN` no `.env` é exatamente igual ao digitado no campo "Verify Token" no painel Meta. Sem espaços extras.

**Mensagens não chegam ao servidor**
→ Verifique se a subscription `messages` está marcada em **Webhook Fields** no painel Meta.
→ Confirme que o túnel ngrok está ativo e a URL está correta no webhook.

**Erro 401 da API Meta**
→ O token temporário expirou (validade de ~24h). Gere um novo no painel ou configure um System User com token permanente.

**Bot não responde**
→ Verifique os logs do servidor. Confirme que `GROQ_API_KEY` é válida acessando [console.groq.com](https://console.groq.com).
→ Confirme que o número está inscrito para receber mensagens do app Meta.

**Bot responde mas depois para**
→ O número pode ter sido adicionado ao set `_escalated_numbers`. Chame `POST /retomar/<numero>` para reativar.

**LLM retorna JSON mesmo sendo resposta de texto**
→ Isso indica que o modelo gerou uma resposta de escalada sem intenção. Ajuste `temperature` para um valor menor (ex.: `0.2`) em `agent.py`.

**Cold start no Render (timeout no webhook)**
→ A Meta exige resposta em menos de 20 segundos. Configure um cron job externo para fazer ping no `/health` a cada 5 minutos e manter o servidor ativo.

---

## Limitações Conhecidas

- **Histórico em memória**: perdido a cada reinicialização do servidor (use Redis para produção)
- **Sem catálogo de produtos**: perguntas sobre medicamentos específicos são sempre escaladas
- **Token temporário da Meta**: expira em ~24h; requer automação ou System User para produção
- **Rate limits do Groq**: no plano gratuito, limites de tokens por minuto podem causar lentidão em pico de uso
- **Sem suporte a grupos**: o bot só responde mensagens diretas (1-1)
- **Sem persistência de `_escalated_numbers`**: ao reiniciar o servidor, números escalados voltam a receber mensagens do bot

---

## Roadmap

- [ ] Persistência de histórico com Redis
- [ ] Painel web para gerenciamento de escaladas e retomadas
- [ ] Suporte a catálogo de produtos via integração com ERP/estoque
- [ ] Métricas de atendimento (total de conversas, taxa de escalada, tempo médio de resposta)
- [ ] Suporte a templates de mensagem Meta (HSM) para campanhas
- [ ] Integração com sistema de agendamento para serviços (injetáveis, testes rápidos)
- [ ] Testes automatizados com pytest

---

## Checklist de Deploy

- [ ] `knowledge_base.json` preenchido com dados reais
- [ ] `.env` configurado com todas as credenciais
- [ ] Servidor hospedado com URL pública HTTPS disponível
- [ ] Webhook registrado e verificado na Meta
- [ ] Subscription `messages` ativada no webhook
- [ ] Número de WhatsApp vinculado ao app e testado
- [ ] `WHATSAPP_ATENDENTE_NUMBER` configurado para receber alertas
- [ ] Token permanente configurado (System User) para produção
- [ ] Health check monitorado externamente

---

## Dependências

```
flask==3.0.3          # Framework web
groq==0.9.0           # SDK oficial do Groq para Python
requests==2.32.3      # Chamadas HTTP para a API Meta
python-dotenv==1.0.1  # Carregamento de variáveis de ambiente do .env
```

---

## Licença

Este projeto é de uso interno. Adapte livremente para seus projetos.
