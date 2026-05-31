"""Testes de integração — api.py: SSE, rate limit, circuit breaker, security headers."""
import json
import os
import pytest
import pytest_asyncio
from unittest.mock import AsyncMock, MagicMock
from httpx import AsyncClient, ASGITransport

# Env vars mínimas antes de importar app
os.environ.setdefault("ANTHROPIC_API_KEY", "sk-test-key")
os.environ.setdefault("DB_PATH", ":memory:")
os.environ.setdefault("RATE_LIMIT_FREE", "10000")

from api import app, _get_daily_cost, _init_db, _hash_ip


# ─── fixtures ─────────────────────────────────────────────────────────────────

@pytest_asyncio.fixture
async def client():
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as c:
        yield c


BODY_VALIDO = {
    "input": "desigualdade social no Brasil",
    "disciplina": "sociologia",
    "tipo": "resumo",
    "banca": None,
}


def _mock_graph_result():
    return {
        "output": {
            "titulo": "Desigualdade Social",
            "topicos": ["Gini", "renda"],
            "texto_resumido": "O Brasil tem alta desigualdade.",
            "fontes": [],
        },
        "tokens_used": 100,
        "cost_usd": 0.001,
    }


# ─── helper: ler eventos SSE ──────────────────────────────────────────────────

def _parse_sse(text: str) -> list[dict]:
    events = []
    for line in text.splitlines():
        if line.startswith("data: ") and line != "data: [DONE]":
            events.append(json.loads(line[6:]))
    return events


# ─── SSE básico ───────────────────────────────────────────────────────────────

@pytest.mark.asyncio
class TestSSE:
    async def test_post_pesquisar_content_type_sse(self, client, mocker):
        mocker.patch("api._run_pipeline", new=AsyncMock(return_value=_mock_graph_result()))
        resp = await client.post("/pesquisar", json=BODY_VALIDO)
        assert resp.status_code == 200
        assert "text/event-stream" in resp.headers["content-type"]

    async def test_post_pesquisar_evento_iniciando(self, client, mocker):
        mocker.patch("api._run_pipeline", new=AsyncMock(return_value=_mock_graph_result()))
        resp = await client.post("/pesquisar", json=BODY_VALIDO)
        events = _parse_sse(resp.text)
        statuses = [e.get("status") for e in events]
        assert "iniciando" in statuses

    async def test_post_pesquisar_evento_concluido_com_output(self, client, mocker):
        mocker.patch("api._run_pipeline", new=AsyncMock(return_value=_mock_graph_result()))
        resp = await client.post("/pesquisar", json=BODY_VALIDO)
        events = _parse_sse(resp.text)
        concluido = next((e for e in events if e.get("status") == "concluido"), None)
        assert concluido is not None
        assert "output" in concluido

    async def test_post_pesquisar_termina_com_done(self, client, mocker):
        mocker.patch("api._run_pipeline", new=AsyncMock(return_value=_mock_graph_result()))
        resp = await client.post("/pesquisar", json=BODY_VALIDO)
        assert "data: [DONE]" in resp.text


# ─── word block ───────────────────────────────────────────────────────────────

@pytest.mark.asyncio
class TestWordBlock:
    async def test_input_bloqueado_retorna_400(self, client):
        body = {**BODY_VALIDO, "input": "como fazer bomba em casa"}
        resp = await client.post("/pesquisar", json=body)
        assert resp.status_code == 400

    async def test_input_valido_nao_bloqueado(self, client, mocker):
        mocker.patch("api._run_pipeline", new=AsyncMock(return_value=_mock_graph_result()))
        resp = await client.post("/pesquisar", json=BODY_VALIDO)
        assert resp.status_code == 200


# ─── circuit breaker ──────────────────────────────────────────────────────────

@pytest.mark.asyncio
class TestCircuitBreaker:
    async def test_custo_acima_cap_retorna_503(self, client, mocker):
        mocker.patch("api._get_daily_cost", return_value=5.01)
        resp = await client.post("/pesquisar", json=BODY_VALIDO)
        assert resp.status_code == 503

    async def test_custo_exato_cap_retorna_503(self, client, mocker):
        mocker.patch("api._get_daily_cost", return_value=5.00)
        resp = await client.post("/pesquisar", json=BODY_VALIDO)
        assert resp.status_code == 503

    async def test_custo_abaixo_cap_prossegue(self, client, mocker):
        mocker.patch("api._get_daily_cost", return_value=4.99)
        mocker.patch("api._run_pipeline", new=AsyncMock(return_value=_mock_graph_result()))
        resp = await client.post("/pesquisar", json=BODY_VALIDO)
        assert resp.status_code == 200


# ─── security headers ─────────────────────────────────────────────────────────

@pytest.mark.asyncio
class TestSecurityHeaders:
    async def test_x_content_type_options(self, client, mocker):
        mocker.patch("api._run_pipeline", new=AsyncMock(return_value=_mock_graph_result()))
        resp = await client.post("/pesquisar", json=BODY_VALIDO)
        assert resp.headers.get("x-content-type-options") == "nosniff"

    async def test_x_frame_options(self, client, mocker):
        mocker.patch("api._run_pipeline", new=AsyncMock(return_value=_mock_graph_result()))
        resp = await client.post("/pesquisar", json=BODY_VALIDO)
        assert resp.headers.get("x-frame-options") == "DENY"

    async def test_referrer_policy(self, client, mocker):
        mocker.patch("api._run_pipeline", new=AsyncMock(return_value=_mock_graph_result()))
        resp = await client.post("/pesquisar", json=BODY_VALIDO)
        assert resp.headers.get("referrer-policy") is not None

    async def test_server_header_removido(self, client, mocker):
        mocker.patch("api._run_pipeline", new=AsyncMock(return_value=_mock_graph_result()))
        resp = await client.post("/pesquisar", json=BODY_VALIDO)
        assert "server" not in resp.headers


# ─── helpers internos ─────────────────────────────────────────────────────────

class TestHashIp:
    def test_hash_deterministic_mesmo_dia(self):
        h1 = _hash_ip("1.2.3.4")
        h2 = _hash_ip("1.2.3.4")
        assert h1 == h2

    def test_hash_ips_diferentes(self):
        assert _hash_ip("1.2.3.4") != _hash_ip("5.6.7.8")

    def test_hash_formato_hex(self):
        h = _hash_ip("1.2.3.4")
        assert len(h) == 64
        int(h, 16)  # valida hex


class TestGetDailyCost:
    def test_retorna_float(self, tmp_path):
        db = str(tmp_path / "test.db")
        _init_db(db)
        cost = _get_daily_cost(db)
        assert isinstance(cost, float)
        assert cost == 0.0
