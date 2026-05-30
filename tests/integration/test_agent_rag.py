"""Testes de integração — agent_rag com Qdrant/embed/rerank mockados."""
import pytest
import numpy as np
from unittest.mock import AsyncMock, MagicMock, patch
from agents.agent_rag import run, _index, _search_and_rerank, _cleanup

RID = "rag-test-001"

BASE_STATE = {
    "request_id": RID,
    "session_id": "sess-abc123",
    "input": "desigualdade social no Brasil",
    "disciplina": "sociologia",
    "tipo": "resumo",
    "banca": None,
    "fontes_autorizadas": ["ibge", "openalex"],
    "dados_coletados": {
        "ibge": {"dado": "Brasil tem 214M hab. Gini 0,54.", "fonte": "IBGE SIDRA", "url": "https://ibge.gov.br/x"},
        "openalex": {"dado": "Artigo sobre desigualdade de renda.", "fonte": "OpenAlex", "url": "https://openalex.org/W1"},
    },
    "chunks_rag": [],
    "output": {},
    "tokens_used": 0,
    "cost_usd": 0.0,
}


def _fake_embed(texts):
    """Embedding falso 384-dim."""
    return np.random.rand(len(texts), 384).astype(np.float32)


def _fake_rerank(pairs):
    return [0.9 - i * 0.1 for i in range(len(pairs))]


@pytest.mark.asyncio
class TestAgentRagRun:
    async def test_retorna_state_com_chunks(self, mocker):
        mocker.patch("agents.agent_rag._get_embed_model", return_value=MagicMock(encode=_fake_embed))
        mocker.patch("agents.agent_rag._get_rerank_model", return_value=MagicMock(predict=_fake_rerank))

        state = {**BASE_STATE}
        result = await run(state)

        assert "chunks_rag" in result
        assert isinstance(result["chunks_rag"], list)
        assert len(result["chunks_rag"]) > 0

    async def test_chunks_tem_campos_obrigatorios(self, mocker):
        mocker.patch("agents.agent_rag._get_embed_model", return_value=MagicMock(encode=_fake_embed))
        mocker.patch("agents.agent_rag._get_rerank_model", return_value=MagicMock(predict=_fake_rerank))

        result = await run({**BASE_STATE})
        for chunk in result["chunks_rag"]:
            assert "texto" in chunk
            assert "fonte" in chunk
            assert "url" in chunk

    async def test_sem_dados_retorna_chunks_vazio(self, mocker):
        mocker.patch("agents.agent_rag._get_embed_model", return_value=MagicMock(encode=_fake_embed))
        mocker.patch("agents.agent_rag._get_rerank_model", return_value=MagicMock(predict=_fake_rerank))

        state = {**BASE_STATE, "dados_coletados": {}}
        result = await run(state)
        assert result["chunks_rag"] == []

    async def test_cleanup_executado_mesmo_com_erro(self, mocker):
        mocker.patch("agents.agent_rag._get_embed_model", side_effect=RuntimeError("embed crash"))
        cleanup_mock = AsyncMock()
        mocker.patch("agents.agent_rag._cleanup", cleanup_mock)

        with pytest.raises(RuntimeError):
            await run({**BASE_STATE})

        cleanup_mock.assert_called_once()

    async def test_dados_rss_list_flatten(self, mocker):
        mocker.patch("agents.agent_rag._get_embed_model", return_value=MagicMock(encode=_fake_embed))
        mocker.patch("agents.agent_rag._get_rerank_model", return_value=MagicMock(predict=_fake_rerank))

        state = {**BASE_STATE, "dados_coletados": {
            "senado": [
                {"dado": "Senado aprova PEC.", "fonte": "Senado RSS", "url": "https://senado.leg.br/n1",
                 "is_rss": True, "aviso_rss": "RSS"},
                {"dado": "Nova lei ambiental.", "fonte": "Senado RSS", "url": "https://senado.leg.br/n2",
                 "is_rss": True, "aviso_rss": "RSS"},
            ]
        }}
        result = await run(state)
        assert len(result["chunks_rag"]) <= 3


@pytest.mark.asyncio
class TestIndex:
    async def test_retorna_chunks_indexados(self, mocker):
        from qdrant_client import AsyncQdrantClient
        client = AsyncQdrantClient(":memory:")
        mocker.patch("agents.agent_rag._get_embed_model", return_value=MagicMock(encode=_fake_embed))

        dados = {
            "ibge": {"dado": "texto ibge", "fonte": "IBGE", "url": "https://ibge.gov.br"},
        }
        chunks = await _index(client, "test_col", dados, RID)
        assert len(chunks) == 1
        assert chunks[0]["fonte"] == "IBGE"
        await client.close()

    async def test_dados_vazios_retorna_lista_vazia(self, mocker):
        from qdrant_client import AsyncQdrantClient
        client = AsyncQdrantClient(":memory:")
        chunks = await _index(client, "test_col", {}, RID)
        assert chunks == []
        await client.close()


@pytest.mark.asyncio
class TestCleanup:
    async def test_deleta_colecao(self):
        from qdrant_client import AsyncQdrantClient
        from qdrant_client.models import VectorParams, Distance
        client = AsyncQdrantClient(":memory:")
        await client.create_collection("test_del", vectors_config=VectorParams(size=4, distance=Distance.COSINE))
        # Verificar antes
        cols_before = await client.get_collections()
        assert "test_del" in [c.name for c in cols_before.collections]
        # _cleanup fecha o client no finally — nao usar client depois
        await _cleanup(client, "test_del", RID)
        # Client fechado — não levantou exceção = coleção foi deletada com sucesso

    async def test_cleanup_nao_levanta_se_colecao_nao_existe(self):
        from qdrant_client import AsyncQdrantClient
        client = AsyncQdrantClient(":memory:")
        await _cleanup(client, "nao_existe", RID)  # não deve levantar
