"""Testes de integração — agent_redator com instructor mockado."""
import pytest
from unittest.mock import MagicMock, patch
from agents.agent_redator import run, _get_schema, _build_prompt, TOKEN_BUDGET
from agents.schemas.redacao_enem import RedacaoENEM, PropostaIntervencaoENEM
from agents.schemas.redacao_fuvest import RedacaoFUVEST
from agents.schemas.redacao_unicamp import RedacaoUNICAMP, PropostaUNICAMP
from agents.schemas.redacao_unesp import RedacaoUNESP
from agents.schemas.resumo import Resumo
from agents.schemas.dpo import DPO, BlocoArgumentativo
from agents.schemas.analise_texto import AnaliseTextoModoA
from agents.schemas.ficha_estudo import FichaEstudo
from agents.schemas.shared import FonteOficial

RID = "redator-test-001"

_CHUNKS = [
    {"texto": "Brasil tem alta desigualdade.", "fonte": "IBGE", "url": "https://ibge.gov.br/x", "is_rss": False},
    {"texto": "Gini 0,54 em 2022.", "fonte": "IPEA", "url": "https://ipea.gov.br/y", "is_rss": False},
]

BASE_STATE = {
    "request_id": RID,
    "session_id": "sess-001",
    "input": "desigualdade social",
    "disciplina": "sociologia",
    "tipo": "resumo",
    "banca": None,
    "fontes_autorizadas": [],
    "dados_coletados": {},
    "chunks_rag": _CHUNKS,
    "output": {},
    "tokens_used": 0,
    "cost_usd": 0.0,
}

_FONTE = FonteOficial(fonte="IBGE", url="https://ibge.gov.br/x")


def _mock_resumo():
    return Resumo(
        titulo="Desigualdade Social no Brasil",
        topicos=["concentração de renda", "Gini"],
        texto_resumido="O Brasil apresenta alta desigualdade.",
        fontes=[_FONTE],
    )


def _mock_redacao_enem():
    return RedacaoENEM(
        introducao="A desigualdade social...",
        desenvolvimento=["Argumento 1...", "Argumento 2..."],
        conclusao="Portanto...",
        proposta_intervencao=PropostaIntervencaoENEM(
            agente="O Estado",
            acao="deve implementar políticas redistributivas",
            meio="por meio de tributação progressiva",
            finalidade="a fim de reduzir o índice Gini",
        ),
        fontes=[_FONTE],
    )


def _make_instructor_mock(return_val):
    mock_client = MagicMock()
    mock_client.chat.completions.create.return_value = return_val
    return mock_client


class TestGetSchema:
    def test_resumo_retorna_resumo(self):
        assert _get_schema("resumo", None) == Resumo

    def test_redacao_enem(self):
        assert _get_schema("redacao", "ENEM") == RedacaoENEM

    def test_redacao_fuvest(self):
        assert _get_schema("redacao", "FUVEST") == RedacaoFUVEST

    def test_redacao_unicamp(self):
        assert _get_schema("redacao", "UNICAMP") == RedacaoUNICAMP

    def test_redacao_unesp(self):
        assert _get_schema("redacao", "UNESP") == RedacaoUNESP

    def test_redacao_sem_banca_fallback_enem(self):
        assert _get_schema("redacao", None) == RedacaoENEM

    def test_dpo_retorna_dpo(self):
        assert _get_schema("dpo", None) == DPO

    def test_analise_texto_retorna_modo_a(self):
        assert _get_schema("analise_texto", None) == AnaliseTextoModoA

    def test_ficha_estudo_retorna_ficha(self):
        assert _get_schema("ficha_estudo", None) == FichaEstudo

    def test_tipo_invalido_levanta_erro(self):
        with pytest.raises(ValueError):
            _get_schema("tipo_inexistente", None)


class TestBuildPrompt:
    def test_tema_dentro_de_tag_xml(self):
        prompt = _build_prompt("resumo", _CHUNKS, "desigualdade social")
        assert "<tema>desigualdade social</tema>" in prompt

    def test_fontes_incluidas(self):
        prompt = _build_prompt("resumo", _CHUNKS, "tema")
        assert "IBGE" in prompt
        assert "IPEA" in prompt

    def test_sem_chunks_nao_quebra(self):
        prompt = _build_prompt("resumo", [], "tema")
        assert "<tema>tema</tema>" in prompt

    def test_tipo_incluido(self):
        prompt = _build_prompt("dpo", _CHUNKS, "tema")
        assert "dpo" in prompt


class TestTokenBudget:
    def test_ficha_tem_maior_budget(self):
        assert TOKEN_BUDGET["ficha_estudo"] == 12000

    def test_resumo_menor_que_redacao(self):
        assert TOKEN_BUDGET["resumo"] < TOKEN_BUDGET["redacao"]


@pytest.mark.asyncio
class TestAgentRedatorRun:
    async def test_resumo_retorna_output(self, mocker):
        mock_instructor = _make_instructor_mock(_mock_resumo())
        mocker.patch("agents.agent_redator._make_instructor_client", return_value=mock_instructor)

        result = await run({**BASE_STATE, "tipo": "resumo"})
        assert result["output"]["titulo"] == "Desigualdade Social no Brasil"

    async def test_redacao_enem_retorna_output(self, mocker):
        mock_instructor = _make_instructor_mock(_mock_redacao_enem())
        mocker.patch("agents.agent_redator._make_instructor_client", return_value=mock_instructor)

        result = await run({**BASE_STATE, "tipo": "redacao", "banca": "ENEM"})
        assert "proposta_intervencao" in result["output"]
        pi = result["output"]["proposta_intervencao"]
        assert all(pi.get(c) for c in ["agente", "acao", "meio", "finalidade"])

    async def test_schema_instructor_chamado_com_modelo_correto(self, mocker):
        mock_instructor = _make_instructor_mock(_mock_resumo())
        mocker.patch("agents.agent_redator._make_instructor_client", return_value=mock_instructor)

        await run({**BASE_STATE, "tipo": "resumo"})

        call_kwargs = mock_instructor.chat.completions.create.call_args.kwargs
        assert call_kwargs["response_model"] == Resumo

    async def test_excecao_propaga(self, mocker):
        mock_instructor = MagicMock()
        mock_instructor.chat.completions.create.side_effect = RuntimeError("API down")
        mocker.patch("agents.agent_redator._make_instructor_client", return_value=mock_instructor)

        with pytest.raises(RuntimeError, match="API down"):
            await run({**BASE_STATE, "tipo": "resumo"})
