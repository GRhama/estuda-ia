import asyncio
import hashlib
import json
import os
import sqlite3
import uuid
from contextlib import asynccontextmanager
from datetime import date, datetime, timezone
from typing import Optional

from fastapi import FastAPI, HTTPException, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import StreamingResponse
from loguru import logger
from pydantic import BaseModel
from pydantic_settings import BaseSettings
from pydantic import ConfigDict
from slowapi import Limiter, _rate_limit_exceeded_handler
from slowapi.errors import RateLimitExceeded
from slowapi.util import get_remote_address
from starlette.middleware.base import BaseHTTPMiddleware

from core.sanitizer import sanitize_user_input, word_block_check


# ─── settings ─────────────────────────────────────────────────────────────────

class Settings(BaseSettings):
    model_config = ConfigDict(env_file=".env", extra="ignore")

    anthropic_api_key: str = "sk-placeholder"
    groq_api_key: Optional[str] = None
    model: str = "claude-sonnet-4-6"
    rate_limit_free: int = 5
    rate_limit_paid: int = 30
    daily_cost_cap_usd: float = 5.00
    debug: bool = False


settings = Settings()
DB_PATH = os.environ.get("DB_PATH", "data/estuda.db")
_semaphore = asyncio.Semaphore(5)


# ─── DB ───────────────────────────────────────────────────────────────────────

def _init_db(db_path: str = DB_PATH) -> None:
    conn = sqlite3.connect(db_path)
    conn.executescript("""
        CREATE TABLE IF NOT EXISTS requests (
            id          TEXT PRIMARY KEY,
            ip_hash     TEXT NOT NULL,
            tipo        TEXT NOT NULL,
            disciplina  TEXT,
            tokens_used INTEGER,
            cost_usd    REAL,
            date        TEXT NOT NULL,
            created_at  TEXT NOT NULL
        );
        CREATE TABLE IF NOT EXISTS rate_limit (
            ip_hash TEXT NOT NULL,
            date    TEXT NOT NULL,
            count   INTEGER DEFAULT 0,
            PRIMARY KEY (ip_hash, date)
        );
        CREATE TABLE IF NOT EXISTS users (
            token_hash TEXT PRIMARY KEY,
            plano      TEXT NOT NULL,
            ativo      INTEGER DEFAULT 1,
            criado_em  TEXT NOT NULL
        );
    """)
    conn.commit()
    conn.close()


def _get_daily_cost(db_path: str = DB_PATH) -> float:
    today = date.today().isoformat()
    try:
        conn = sqlite3.connect(db_path)
        row = conn.execute(
            "SELECT COALESCE(SUM(cost_usd), 0.0) FROM requests WHERE date = ?", (today,)
        ).fetchone()
        conn.close()
        return float(row[0]) if row else 0.0
    except Exception:
        return 0.0


def _record_request(
    request_id: str,
    ip_hash: str,
    tipo: str,
    disciplina: Optional[str],
    tokens_used: int,
    cost_usd: float,
    db_path: str = DB_PATH,
) -> None:
    today = date.today().isoformat()
    now = datetime.now(timezone.utc).isoformat()
    try:
        conn = sqlite3.connect(db_path)
        conn.execute(
            "INSERT INTO requests VALUES (?,?,?,?,?,?,?,?)",
            (request_id, ip_hash, tipo, disciplina, tokens_used, cost_usd, today, now),
        )
        conn.execute(
            "INSERT INTO rate_limit (ip_hash, date, count) VALUES (?,?,1) "
            "ON CONFLICT(ip_hash, date) DO UPDATE SET count = count + 1",
            (ip_hash, today),
        )
        conn.commit()
        conn.close()
    except Exception as e:
        logger.warning(f"DB record falhou: {type(e).__name__}")


def _hash_ip(ip: str) -> str:
    salt = os.environ.get("IP_SALT", date.today().isoformat())
    return hashlib.sha256(f"{ip}{salt}".encode()).hexdigest()


# ─── pipeline wrapper (mockable) ──────────────────────────────────────────────

async def _run_pipeline(state: dict) -> dict:
    from graph import graph
    return await graph.ainvoke(state)


# ─── limiter ──────────────────────────────────────────────────────────────────

limiter = Limiter(key_func=get_remote_address)


# ─── lifespan ─────────────────────────────────────────────────────────────────

@asynccontextmanager
async def lifespan(app: FastAPI):
    if DB_PATH != ":memory:":
        os.makedirs(os.path.dirname(DB_PATH) if os.path.dirname(DB_PATH) else ".", exist_ok=True)
    _init_db(DB_PATH)
    logger.info("API iniciada. DB OK.")
    yield
    logger.info("API encerrada.")


# ─── app ──────────────────────────────────────────────────────────────────────

app = FastAPI(lifespan=lifespan)
app.state.limiter = limiter
app.add_exception_handler(RateLimitExceeded, _rate_limit_exceeded_handler)

app.add_middleware(
    CORSMiddleware,
    allow_origins=os.environ.get("CORS_ORIGINS", "").split(",") or ["*"],
    allow_methods=["POST", "GET"],
    allow_headers=["Content-Type", "Authorization"],
)


class SecurityHeadersMiddleware(BaseHTTPMiddleware):
    async def dispatch(self, request: Request, call_next):
        response = await call_next(request)
        response.headers["X-Content-Type-Options"] = "nosniff"
        response.headers["X-Frame-Options"] = "DENY"
        response.headers["X-XSS-Protection"] = "1; mode=block"
        response.headers["Referrer-Policy"] = "strict-origin-when-cross-origin"
        response.headers["Permissions-Policy"] = "geolocation=(), microphone=()"
        if "server" in response.headers:
            del response.headers["server"]
        return response


app.add_middleware(SecurityHeadersMiddleware)


# ─── request schema ───────────────────────────────────────────────────────────

class PesquisarRequest(BaseModel):
    input: str
    disciplina: str
    tipo: str
    banca: Optional[str] = None
    trecho: Optional[str] = None


# ─── endpoint ─────────────────────────────────────────────────────────────────

@app.post("/pesquisar")
@limiter.limit(f"{settings.rate_limit_free}/day")
async def pesquisar(request: Request, body: PesquisarRequest):
    # circuit breaker
    if _get_daily_cost() >= settings.daily_cost_cap_usd:
        logger.warning("circuit_breaker: custo diário atingiu o limite")
        raise HTTPException(status_code=503, detail="Serviço temporariamente indisponível")

    # sanitize + word block
    try:
        sanitized = sanitize_user_input(body.input)
    except ValueError:
        raise HTTPException(status_code=400, detail="Requisição não pode ser processada")
    if word_block_check(sanitized):
        raise HTTPException(status_code=400, detail="Requisição não pode ser processada")

    ip = get_remote_address(request)
    ip_hash = _hash_ip(ip)
    request_id = str(uuid.uuid4())

    async def generate():
        yield f"data: {json.dumps({'status': 'iniciando', 'request_id': request_id})}\n\n"

        async with _semaphore:
            yield f"data: {json.dumps({'status': 'processando'})}\n\n"
            try:
                from graph import GraphState
                state: GraphState = {
                    "request_id": request_id,
                    "input": sanitized,
                    "disciplina": body.disciplina,
                    "tipo": body.tipo,
                    "banca": body.banca,
                    "trecho": body.trecho,
                    "fontes_autorizadas": [],
                    "dados_coletados": {},
                    "chunks_rag": [],
                    "output": {},
                    "tokens_used": 0,
                    "cost_usd": 0.0,
                    "session_id": request_id,
                }
                result = await _run_pipeline(state)
                output = result.get("output", {})
                tokens = result.get("tokens_used", 0)
                cost = result.get("cost_usd", 0.0)

                _record_request(request_id, ip_hash, body.tipo, body.disciplina, tokens, cost)

                yield f"data: {json.dumps({'status': 'concluido', 'output': output})}\n\n"
            except Exception as e:
                logger.error(f"[{request_id}] pipeline falhou: {type(e).__name__}")
                yield f"data: {json.dumps({'status': 'erro', 'mensagem': 'Erro interno'})}\n\n"

        yield "data: [DONE]\n\n"

    return StreamingResponse(generate(), media_type="text/event-stream")


@app.get("/health")
async def health():
    return {"status": "ok", "custo_hoje": _get_daily_cost()}
