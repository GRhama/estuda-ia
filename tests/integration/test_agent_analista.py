"""Testes de integração — agent_analista (Modo A e Modo B) + CA-04 + CA-05."""
import pytest
from unittest.mock import MagicMock
from agents.agent_analista import run, _build_prompt, _detect_modo
from agents.schemas.analise_texto import AnaliseTextoModoA, AnaliseTextoModoB

RID = "analista-test-001"

_CHUNKS = [
    {"texto": "Machado de Assis usou ironia como recurso central.", "fonte": "OpenAlex", "url": "https://openalex.org/W1"},
    {"texto": "Dom Casmurro narra em primeira pessoa.", "fonte": "Wikipedia PT", "url": "https://pt.wikipedia.org/wiki/Dom_Casmurro"},
]

BASE_STATE = {
    "request_id": RID,
    "session_id": "sess-001",
    "input": "Dom Casmurro de Machado de Assis",
    "disciplina": "literatura",
    "tipo": "analise_texto",
    "banca": None,
    "trecho": None,
    "fontes_autorizadas": [],
    "dados_coletados": {},
    "chunks_rag": _CHUNKS,
    "output": {},
    "tokens_used": 0,
    "cost_usd": 0.0,
}

_FONTE_URL = "https://pt.wikipedia.org/wiki/Dom_Casmurro"


def _mock_modo_a():
    from agents.schemas.analise_texto import RecursoEstilistico
    return AnaliseTextoModoA(
        titulo_obra="Dom Casmurro",
        autor="Machado de Assis",
        recursos_estilisticos=[
            RecursoEstilistico(
                recurso="ironia",
                trecho="O tempo era de paz.",
                efeito="contraste com o conflito interno do narrador",
            )
        ],
        temas=["ciúme", "memória", "narrador não confiável"],
    )


def _mock_modo_b():
    return AnaliseTextoModoB(
        titulo_obra="Dom Casmurro",
        autor="Machado de Assis",
        recursos_estilisticos=[],
        temas=["ciúme", "traição"],
        limitacao="Análise baseada em fontes secundárias — texto não fornecido pelo usuário.",
    )


def _make_mock(return_val):
    m = MagicMock()
    m.chat.completions.create.return_value = return_val
    return m


# ─── _detect_modo ────────────────────────────────────────────────────────────

class TestDetectModo:
    def test_trecho_presente_retorna_A(self):
        assert _detect_modo("texto qualquer") == "A"

    def test_trecho_none_retorna_B(self):
        assert _detect_modo(None) == "B"

    def test_trecho_vazio_retorna_B(self):
        assert _detect_modo("") == "B"

    def test_trecho_so_espacos_retorna_B(self):
        assert _detect_modo("   ") == "B"


# ─── _build_prompt ────────────────────────────────────────────────────────────

class TestBuildPrompt:
    def test_tema_em_tag_xml(self):
        p = _build_prompt(_CHUNKS, "Dom Casmurro", None, "B")
        assert "<tema>Dom Casmurro</tema>" in p

    def test_modo_b_sem_trecho_indica_fontes_secundarias(self):
        p = _build_prompt(_CHUNKS, "tema", None, "B")
        assert "Modo B" in p or "título/autor" in p.lower()

    def test_modo_a_com_trecho_inclui_trecho(self):
        p = _build_prompt(_CHUNKS, "tema", "Capítulo I: Do título...", "A")
        assert "Capítulo I: Do título..." in p

    def test_fontes_incluidas(self):
        p = _build_prompt(_CHUNKS, "tema", None, "B")
        assert "OpenAlex" in p
        assert "Wikipedia PT" in p


# ─── run — Modo A ─────────────────────────────────────────────────────────────

@pytest.mark.asyncio
class TestAgentAnalistaModoA:
    """CA-04: Análise com trecho fornecido → AnaliseTextoModoA."""

    async def test_ca04_modo_a_retorna_schema_correto(self, mocker):
        mocker.patch("agents.agent_analista._make_instructor_client",
                     return_value=_make_mock(_mock_modo_a()))
        state = {**BASE_STATE, "trecho": "O tempo era de paz. A cidade dormia."}
        result = await run(state)
        assert result["output"]["modo"] == "trecho"

    async def test_ca04_recursos_estilisticos_presentes(self, mocker):
        mocker.patch("agents.agent_analista._make_instructor_client",
                     return_value=_make_mock(_mock_modo_a()))
        result = await run({**BASE_STATE, "trecho": "texto"})
        assert len(result["output"]["recursos_estilisticos"]) > 0

    async def test_ca04_temas_presentes(self, mocker):
        mocker.patch("agents.agent_analista._make_instructor_client",
                     return_value=_make_mock(_mock_modo_a()))
        result = await run({**BASE_STATE, "trecho": "texto"})
        assert len(result["output"]["temas"]) > 0

    async def test_ca04_instructor_recebe_schema_modo_a(self, mocker):
        mock_client = _make_mock(_mock_modo_a())
        mocker.patch("agents.agent_analista._make_instructor_client", return_value=mock_client)
        await run({**BASE_STATE, "trecho": "texto"})
        call_kw = mock_client.chat.completions.create.call_args.kwargs
        assert call_kw["response_model"] == AnaliseTextoModoA


# ─── run — Modo B ─────────────────────────────────────────────────────────────

@pytest.mark.asyncio
class TestAgentAnalistaModoB:
    """CA-05: Análise sem trecho → AnaliseTextoModoB com limitacao obrigatório."""

    async def test_ca05_modo_b_retorna_schema_correto(self, mocker):
        mocker.patch("agents.agent_analista._make_instructor_client",
                     return_value=_make_mock(_mock_modo_b()))
        result = await run({**BASE_STATE, "trecho": None})
        assert result["output"]["modo"] == "titulo_autor"

    async def test_ca05_limitacao_presente(self, mocker):
        mocker.patch("agents.agent_analista._make_instructor_client",
                     return_value=_make_mock(_mock_modo_b()))
        result = await run({**BASE_STATE, "trecho": None})
        assert result["output"]["limitacao"]
        assert len(result["output"]["limitacao"].strip()) > 0

    async def test_ca05_instructor_recebe_schema_modo_b(self, mocker):
        mock_client = _make_mock(_mock_modo_b())
        mocker.patch("agents.agent_analista._make_instructor_client", return_value=mock_client)
        await run({**BASE_STATE, "trecho": None})
        call_kw = mock_client.chat.completions.create.call_args.kwargs
        assert call_kw["response_model"] == AnaliseTextoModoB

    async def test_ca05_trecho_vazio_usa_modo_b(self, mocker):
        mocker.patch("agents.agent_analista._make_instructor_client",
                     return_value=_make_mock(_mock_modo_b()))
        result = await run({**BASE_STATE, "trecho": ""})
        assert result["output"]["modo"] == "titulo_autor"

    async def test_ca05_excecao_propaga(self, mocker):
        mock_client = MagicMock()
        mock_client.chat.completions.create.side_effect = RuntimeError("API down")
        mocker.patch("agents.agent_analista._make_instructor_client", return_value=mock_client)
        with pytest.raises(RuntimeError, match="API down"):
            await run({**BASE_STATE, "trecho": None})
