# Estuda.IA

Plataforma de pesquisa acadêmica multi-agente para estudantes do 3º ano do EM prestando FUVEST, ENEM, UNESP e UNICAMP. Toda resposta tem fonte rastreável — o sistema **nunca responde do próprio conhecimento**.

**Usuária primária:** Catarina, 17 anos, só celular, conexão 3G.

---

## Stack

| Camada | Tecnologia |
|--------|-----------|
| Orquestração | LangGraph (`StateGraph`) |
| LLM | Claude Sonnet 4 (`claude-sonnet-4-6`) |
| Structured Output | `instructor` + Pydantic v2 |
| RAG | LlamaIndex + Qdrant local (ephemeral por sessão) |
| Embedding | `all-MiniLM-L6-v2` (local, gratuito) |
| Rerank | `cross-encoder/ms-marco-MiniLM-L-6-v2` (local) |
| HTTP | `httpx.AsyncClient` |
| Backend | FastAPI + SSE streaming |
| Rate Limit | `slowapi` (por IP) + SQLite (persistência) |
| Frontend | PWA mobile-first — HTML/CSS/JS puro |
| Deploy | Docker Compose + Caddy (HTTPS automático) |

---

## Arquitetura

```
[PWA Mobile]
     │  POST /pesquisar {input, disciplina, tipo, banca?}
     ▼
[FastAPI — SSE streaming]
  ├── Sanitização + word-block
  ├── Rate limit (slowapi + SQLite)
  ├── Semaphore(5): máx 5 pipelines simultâneos
  └── Circuit breaker: custo > $5/dia → 503
     │
     ▼
[LangGraph]
  Router → AgentDados → AgentRAG ──┬── (sem chunks) → Fallback
                                   ├── AgentRedator → (ficha_estudo) → AgentExercicios
                                   └── AgentAnalista (analise_texto)
```

**Guardrail principal:** afirmação sem fonte → `"Informação não localizada em fonte oficial"`. O LLM nunca inventa dado.

**CA-07 Fallback:** se nenhuma fonte retornar dados (`chunks_rag = []`), o pipeline não chama o LLM — retorna resposta padronizada sem alucinação.

---

## Tipos de output suportados

| `tipo` | `banca` | Output |
|--------|---------|--------|
| `resumo` | — | Resumo com tópicos e fontes |
| `redacao` | `ENEM` / `FUVEST` / `UNICAMP` / `UNESP` | Redação estruturada por banca |
| `dpo` | — | Dissertação por pontos (DPO) |
| `analise_texto` | — | Análise estilística (Modo A: trecho / Modo B: título+autor) |
| `ficha_estudo` | — | Ficha com 15 exercícios (distribuição 5 exatas / 7 humanas / 3 interdisciplinar) |

---

## Fontes autorizadas

19 APIs públicas: IBGE, IPEA, WorldBank, INPE, OMS/PAHO, LexML, Senado RSS, Gov.br RSS, REST Countries, UNESCO WHC, Wikidata, FAO, ONU, Wikipedia PT/EN, OpenAlex, SciELO, PubMed, Gutenberg/Gutendex, Domínio Público MEC.

SSRF bloqueado: qualquer URL fora desta lista é rejeitada em `safe_fetch()`.

---

## Rodando localmente

### Pré-requisitos

```bash
git clone https://github.com/GRhama/estuda-ia
cd estuda-ia
python3 -m venv .venv && source .venv/bin/activate
pip install -r requirements.txt
```

### Variáveis de ambiente

```bash
cp .env.example .env
# Preencha:
# ANTHROPIC_API_KEY=sk-ant-...
# IP_SALT=<string aleatória>
```

### API de desenvolvimento

```bash
uvicorn api:app --reload --host 127.0.0.1 --port 8000
```

### Testes

```bash
# Suite completa (sem real_api)
pytest

# Com cobertura detalhada
pytest --cov=agents --cov=core --cov-report=html

# Testes E2E com APIs reais (requer ANTHROPIC_API_KEY)
pytest -m real_api tests/e2e/
```

---

## Deploy com Docker Compose

```bash
cp .env.example .env   # preencha ANTHROPIC_API_KEY, IP_SALT, CORS_ORIGINS
docker compose up -d
docker compose logs api -f
```

Caddy cuida do HTTPS automático via Let's Encrypt. Configure seu domínio apontando para o servidor antes de subir.

### Variáveis necessárias em produção

| Variável | Descrição |
|----------|-----------|
| `ANTHROPIC_API_KEY` | Chave da API Anthropic |
| `IP_SALT` | Salt para hash de IPs (string aleatória) |
| `CORS_ORIGINS` | Domínio do PWA (ex: `https://estudaia.app`) |
| `MODEL` | Modelo Claude (padrão: `claude-sonnet-4-6`) |
| `DAILY_COST_CAP_USD` | Limite de custo diário em USD (padrão: `5.00`) |
| `RATE_LIMIT_FREE` | Requisições/dia por IP no plano gratuito (padrão: `5`) |

---

## Endpoint

### `POST /pesquisar`

Retorna Server-Sent Events (SSE).

**Request:**
```json
{
  "input": "desigualdade social no Brasil",
  "disciplina": "sociologia",
  "tipo": "resumo",
  "banca": null,
  "trecho": null
}
```

**Eventos SSE:**
```
data: {"status": "iniciando", "request_id": "uuid"}
data: {"status": "processando"}
data: {"status": "concluido", "output": {...}}
data: [DONE]
```

**Fallback CA-07 (sem fontes disponíveis):**
```json
{"status": "concluido", "output": {
  "mensagem": "Informação não localizada em fonte oficial",
  "fontes": []
}}
```

### `GET /health`

```json
{"status": "ok", "custo_hoje": 0.42}
```

---

## Cobertura de testes

```
310 testes | 85% cobertura | 100% guardrails e security
```

- `tests/unit/` — schemas, router, sanitizer, guardrails
- `tests/integration/` — agentes com APIs mockadas (respx + AsyncMock)
- `tests/security/` — prompt injection, SSRF, SQL injection, rate limit bypass
- `tests/e2e/` — pipelines completos (`-m real_api` para APIs reais)
