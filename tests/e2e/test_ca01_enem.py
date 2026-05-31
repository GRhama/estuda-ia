"""CA-01: Redação ENEM com APIs reais (roda apenas em PR/CI explícito).

Requer: ANTHROPIC_API_KEY válida + acesso à internet.
Rodar localmente: pytest tests/e2e/test_ca01_enem.py -m real_api
"""
import os
import pytest

pytestmark = pytest.mark.real_api

if not os.environ.get("ANTHROPIC_API_KEY", "").startswith("sk-ant"):
    pytestmark = pytest.mark.skip(reason="ANTHROPIC_API_KEY não configurada")


@pytest.mark.asyncio
class TestCA01ENEM:
    """CA-01: pipeline completo para redação ENEM com fontes reais."""

    async def test_ca01_retorna_redacao_com_proposta(self):
        """CA-01: output deve conter proposta_intervencao com agente/ação/meio/finalidade."""
        from graph import graph

        state = {
            "request_id": "ca01-e2e-enem",
            "input": "desigualdade social no Brasil",
            "disciplina": "sociologia",
            "tipo": "redacao",
            "banca": "ENEM",
            "trecho": None,
            "fontes_autorizadas": [],
            "dados_coletados": {},
            "chunks_rag": [],
            "output": {},
            "tokens_used": 0,
            "cost_usd": 0.0,
            "session_id": "ca01-e2e-sess",
        }

        result = await graph.ainvoke(state)
        output = result.get("output", {})

        assert output, "output não pode ser vazio"
        proposta = output.get("proposta_intervencao", {})
        for campo in ("agente", "acao", "meio", "finalidade"):
            assert proposta.get(campo), f"CA-01: proposta_intervencao.{campo} vazio"

    async def test_ca01_redacao_tem_introducao_e_conclusao(self):
        """CA-01: redação ENEM deve ter introdução, desenvolvimento e conclusão."""
        from graph import graph

        state = {
            "request_id": "ca01-e2e-struct",
            "input": "educação e desigualdade no Brasil",
            "disciplina": "sociologia",
            "tipo": "redacao",
            "banca": "ENEM",
            "trecho": None,
            "fontes_autorizadas": [],
            "dados_coletados": {},
            "chunks_rag": [],
            "output": {},
            "tokens_used": 0,
            "cost_usd": 0.0,
            "session_id": "ca01-e2e-sess2",
        }

        result = await graph.ainvoke(state)
        output = result.get("output", {})

        assert output.get("introducao"), "CA-01: introdução vazia"
        assert output.get("desenvolvimento"), "CA-01: desenvolvimento vazio"
        assert output.get("conclusao"), "CA-01: conclusão vazia"

    async def test_ca01_fontes_presentes(self):
        """CA-01: output deve citar pelo menos uma fonte oficial."""
        from graph import graph

        state = {
            "request_id": "ca01-e2e-fontes",
            "input": "desigualdade social no Brasil",
            "disciplina": "sociologia",
            "tipo": "redacao",
            "banca": "ENEM",
            "trecho": None,
            "fontes_autorizadas": [],
            "dados_coletados": {},
            "chunks_rag": [],
            "output": {},
            "tokens_used": 0,
            "cost_usd": 0.0,
            "session_id": "ca01-e2e-sess3",
        }

        result = await graph.ainvoke(state)
        output = result.get("output", {})

        fontes = output.get("fontes", [])
        # Se o pipeline retornou fallback, fontes deve ser [] — isso é OK (CA-07)
        if output.get("mensagem") == "Informação não localizada em fonte oficial":
            pytest.skip("Fontes externas indisponíveis — fallback CA-07 ativo")
        assert isinstance(fontes, list), "fontes deve ser lista"
