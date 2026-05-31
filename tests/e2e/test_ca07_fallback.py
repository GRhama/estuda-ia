"""CA-07: fallback sem alucinação quando nenhuma fonte retorna dados."""
import pytest
from unittest.mock import AsyncMock

RID = "ca07-test-001"

_BASE_STATE = {
    "request_id": RID,
    "input": "tema sem fontes",
    "disciplina": "historia",
    "tipo": "resumo",
    "banca": None,
    "trecho": None,
    "fontes_autorizadas": [],
    "dados_coletados": {},
    "chunks_rag": [],
    "output": {},
    "tokens_used": 0,
    "cost_usd": 0.0,
    "session_id": "ca07-sess-001",
}


def _mocked_dados(state):
    return {**state, "dados_coletados": {}}


def _mocked_rag(state):
    return {**state, "chunks_rag": []}


@pytest.mark.asyncio
class TestCA07Fallback:
    """CA-07: sem chunks RAG → pipeline retorna resposta de fallback sem chamar LLM."""

    async def test_pipeline_sem_chunks_retorna_output(self, mocker):
        from graph import graph
        mocker.patch("agents.agent_dados.run", new=AsyncMock(side_effect=_mocked_dados))
        mocker.patch("agents.agent_rag.run", new=AsyncMock(side_effect=_mocked_rag))

        result = await graph.ainvoke(_BASE_STATE)

        assert result.get("output") is not None
        assert result["output"] != {}

    async def test_fallback_mensagem_sem_alucinacao(self, mocker):
        """CA-07: output deve indicar que a informação não foi localizada."""
        from graph import graph
        mocker.patch("agents.agent_dados.run", new=AsyncMock(side_effect=_mocked_dados))
        mocker.patch("agents.agent_rag.run", new=AsyncMock(side_effect=_mocked_rag))

        result = await graph.ainvoke(_BASE_STATE)

        assert result["output"].get("mensagem") == "Informação não localizada em fonte oficial"

    async def test_fallback_fontes_vazia(self, mocker):
        """CA-07: fontes deve ser lista vazia — sem dados inventados."""
        from graph import graph
        mocker.patch("agents.agent_dados.run", new=AsyncMock(side_effect=_mocked_dados))
        mocker.patch("agents.agent_rag.run", new=AsyncMock(side_effect=_mocked_rag))

        result = await graph.ainvoke(_BASE_STATE)

        assert result["output"].get("fontes") == []

    async def test_fallback_nao_chama_agent_redator(self, mocker):
        """CA-07: agent_redator não deve ser invocado quando não há chunks."""
        from graph import graph
        mock_redator = mocker.patch("agents.agent_redator.run")
        mocker.patch("agents.agent_dados.run", new=AsyncMock(side_effect=_mocked_dados))
        mocker.patch("agents.agent_rag.run", new=AsyncMock(side_effect=_mocked_rag))

        await graph.ainvoke(_BASE_STATE)

        mock_redator.assert_not_called()

    async def test_fallback_nao_chama_agent_analista(self, mocker):
        """CA-07: agent_analista também não deve ser chamado."""
        from graph import graph
        mock_analista = mocker.patch("agents.agent_analista.run")
        mocker.patch("agents.agent_dados.run", new=AsyncMock(side_effect=_mocked_dados))
        mocker.patch("agents.agent_rag.run", new=AsyncMock(side_effect=_mocked_rag))

        await graph.ainvoke(_BASE_STATE)

        mock_analista.assert_not_called()

    async def test_fallback_nao_levanta_excecao(self, mocker):
        """CA-07: pipeline não lança exceção com zero dados."""
        from graph import graph
        mocker.patch("agents.agent_dados.run", new=AsyncMock(side_effect=_mocked_dados))
        mocker.patch("agents.agent_rag.run", new=AsyncMock(side_effect=_mocked_rag))

        try:
            result = await graph.ainvoke(_BASE_STATE)
            assert result is not None
        except Exception as exc:
            pytest.fail(f"Pipeline levantou exceção inesperada: {exc}")

    async def test_fallback_todos_tipos(self, mocker, tipo):
        """CA-07: fallback funciona para todos os tipos de output."""
        from graph import graph
        mocker.patch("agents.agent_dados.run", new=AsyncMock(side_effect=_mocked_dados))
        mocker.patch("agents.agent_rag.run", new=AsyncMock(side_effect=_mocked_rag))
        state = {**_BASE_STATE, "tipo": tipo}

        result = await graph.ainvoke(state)

        assert result["output"].get("mensagem") == "Informação não localizada em fonte oficial"

    @pytest.fixture(params=["resumo", "dpo", "ficha_estudo"])
    def tipo(self, request):
        return request.param
