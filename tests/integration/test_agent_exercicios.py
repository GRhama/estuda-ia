"""Testes de integração — agent_exercicios + CA-08 + CA-09."""
import pytest
from unittest.mock import MagicMock, AsyncMock
from pydantic import ValidationError
from agents.agent_exercicios import run, _gerar_exercicio_com_retry, _build_prompt
from agents.schemas.exercicio import (
    AlternativasQuestao,
    ExercicioMultiplaEscolha,
    ResolucaoQuestao,
)

RID = "exercicios-test-001"


def _alt():
    return AlternativasQuestao(a="A", b="B", c="C", d="D", e="E")


def _ex_exatas(conceito: str = "cálculo"):
    return ExercicioMultiplaEscolha(
        enunciado="Calcule x",
        alternativas=_alt(),
        resolucao=ResolucaoQuestao(
            resposta_correta="a", explicacao="ok", passo_a_passo=["p1"], por_que_incorretas={}
        ),
        area="exatas",
        conceito=conceito,
    )


def _ex_humanas(conceito: str = "história"):
    return ExercicioMultiplaEscolha(
        enunciado="Contexto histórico?",
        alternativas=_alt(),
        resolucao=ResolucaoQuestao(
            resposta_correta="b",
            explicacao="ok",
            passo_a_passo=[],
            por_que_incorretas={"a": "errado", "c": "errado", "d": "errado", "e": "errado"},
        ),
        area="humanas",
        conceito=conceito,
    )


def _ex_linguagens(conceito: str = "metáfora"):
    return ExercicioMultiplaEscolha(
        enunciado="Identifique o recurso",
        alternativas=_alt(),
        resolucao=ResolucaoQuestao(resposta_correta="c", explicacao="ok", passo_a_passo=[], por_que_incorretas={}),
        area="linguagens",
        conceito=conceito,
    )


def _make_15_side_effects():
    resps = []
    for i in range(5):
        resps.append(_ex_exatas(f"exatas_{i}"))
    for i in range(7):
        resps.append(_ex_humanas(f"humanas_{i}"))
    for i in range(3):
        resps.append(_ex_linguagens(f"ling_{i}"))
    return resps


def _mock_client(side_effects):
    m = MagicMock()
    m.messages.create = AsyncMock(side_effect=side_effects)
    return m


BASE_STATE = {
    "request_id": RID,
    "session_id": "sess-001",
    "input": "desigualdade social",
    "disciplina": "sociologia",
    "tipo": "ficha_estudo",
    "banca": None,
    "trecho": None,
    "fontes_autorizadas": [],
    "dados_coletados": {},
    "chunks_rag": [],
    "output": {
        "resumo": "resumo sobre desigualdade",
        "pontos_chave": ["ponto 1"],
        "exercicios": [],
        "fontes": [],
    },
    "tokens_used": 0,
    "cost_usd": 0.0,
}


# ─── _build_prompt ────────────────────────────────────────────────────────────

class TestBuildPrompt:
    def test_area_no_prompt(self):
        p = _build_prompt("tema", "exatas", [], [])
        assert "exatas" in p.lower()

    def test_tema_em_tag_xml(self):
        p = _build_prompt("desigualdade", "humanas", [], [])
        assert "<tema>desigualdade</tema>" in p

    def test_conceitos_usados_no_prompt(self):
        p = _build_prompt("tema", "exatas", [], ["cálculo", "geometria"])
        assert "cálculo" in p
        assert "geometria" in p


# ─── _gerar_exercicio_com_retry ───────────────────────────────────────────────

@pytest.mark.asyncio
class TestGerarExercicioComRetry:
    async def test_sucesso_primeira_tentativa(self):
        ex = _ex_exatas("cálculo")
        client = _mock_client([ex])
        result = await _gerar_exercicio_com_retry(client, "claude-test", "tema", "exatas", [], [], RID)
        assert result.conceito == "cálculo"
        assert client.messages.create.call_count == 1

    async def test_retry_em_excecao_segunda_tentativa_ok(self):
        ex = _ex_exatas("cálculo")
        client = _mock_client([RuntimeError("falhou"), ex])
        result = await _gerar_exercicio_com_retry(client, "claude-test", "tema", "exatas", [], [], RID)
        assert result.conceito == "cálculo"
        assert client.messages.create.call_count == 2

    async def test_max_3_tentativas_propaga_excecao(self):
        client = _mock_client([RuntimeError("falhou")] * 3)
        with pytest.raises(RuntimeError, match="falhou"):
            await _gerar_exercicio_com_retry(client, "claude-test", "tema", "exatas", [], [], RID)
        assert client.messages.create.call_count == 3

    async def test_conceito_duplicado_tenta_novamente(self):
        ex_dup = _ex_exatas("cálculo")
        ex_novo = _ex_exatas("geometria")
        client = _mock_client([ex_dup, ex_novo])
        result = await _gerar_exercicio_com_retry(
            client, "claude-test", "tema", "exatas", [], ["cálculo"], RID
        )
        assert result.conceito == "geometria"
        assert client.messages.create.call_count == 2

    async def test_duplicata_persiste_3_tentativas_raise(self):
        ex_dup = _ex_exatas("cálculo")
        client = _mock_client([ex_dup, ex_dup, ex_dup])
        with pytest.raises(RuntimeError):
            await _gerar_exercicio_com_retry(
                client, "claude-test", "tema", "exatas", [], ["cálculo"], RID
            )


# ─── CA-08: run gera 15 exercícios 5/7/3 ─────────────────────────────────────

@pytest.mark.asyncio
class TestCA08Exercicios:
    async def test_ca08_gera_15_exercicios(self, mocker):
        mocker.patch(
            "agents.agent_exercicios._make_instructor_client",
            return_value=_mock_client(_make_15_side_effects()),
        )
        result = await run(BASE_STATE)
        assert len(result["output"]["exercicios"]) == 15

    async def test_ca08_distribuicao_5_7_3(self, mocker):
        mocker.patch(
            "agents.agent_exercicios._make_instructor_client",
            return_value=_mock_client(_make_15_side_effects()),
        )
        result = await run(BASE_STATE)
        exs = result["output"]["exercicios"]
        exatas = sum(1 for e in exs if e["area"] == "exatas")
        humanas = sum(1 for e in exs if e["area"] == "humanas")
        linguagens = sum(1 for e in exs if e["area"] == "linguagens")
        assert exatas == 5
        assert humanas == 7
        assert linguagens == 3

    async def test_ca08_exercicios_tem_enunciado(self, mocker):
        mocker.patch(
            "agents.agent_exercicios._make_instructor_client",
            return_value=_mock_client(_make_15_side_effects()),
        )
        result = await run(BASE_STATE)
        for ex in result["output"]["exercicios"]:
            assert ex["enunciado"]

    async def test_ca08_exatas_tem_passo_a_passo(self, mocker):
        mocker.patch(
            "agents.agent_exercicios._make_instructor_client",
            return_value=_mock_client(_make_15_side_effects()),
        )
        result = await run(BASE_STATE)
        for ex in result["output"]["exercicios"]:
            if ex["area"] == "exatas":
                assert ex["resolucao"]["passo_a_passo"]

    async def test_ca08_humanas_tem_por_que_incorretas(self, mocker):
        mocker.patch(
            "agents.agent_exercicios._make_instructor_client",
            return_value=_mock_client(_make_15_side_effects()),
        )
        result = await run(BASE_STATE)
        for ex in result["output"]["exercicios"]:
            if ex["area"] == "humanas":
                assert ex["resolucao"]["por_que_incorretas"]

    async def test_ca08_output_preserva_resumo(self, mocker):
        mocker.patch(
            "agents.agent_exercicios._make_instructor_client",
            return_value=_mock_client(_make_15_side_effects()),
        )
        result = await run(BASE_STATE)
        assert result["output"]["resumo"] == "resumo sobre desigualdade"


# ─── CA-09: retry guardrail REGRA 7 ───────────────────────────────────────────

@pytest.mark.asyncio
class TestCA09GuardrailRegra7:
    async def test_ca09_retry_conta_chamadas(self, mocker):
        """Primeira chamada falha, segunda ok. Deve chamar 2x para aquele exercício."""
        responses = [RuntimeError("API down")] + _make_15_side_effects()
        mock_c = _mock_client(responses)
        mocker.patch("agents.agent_exercicios._make_instructor_client", return_value=mock_c)
        result = await run(BASE_STATE)
        # 1 retry extra = 16 total calls
        assert mock_c.messages.create.call_count == 16
        assert len(result["output"]["exercicios"]) == 15

    async def test_ca09_conceitos_unicos(self, mocker):
        mocker.patch(
            "agents.agent_exercicios._make_instructor_client",
            return_value=_mock_client(_make_15_side_effects()),
        )
        result = await run(BASE_STATE)
        conceitos = [e["conceito"] for e in result["output"]["exercicios"]]
        assert len(conceitos) == len(set(conceitos)), "conceitos duplicados encontrados"
