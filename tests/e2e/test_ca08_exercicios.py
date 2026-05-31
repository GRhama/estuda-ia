"""CA-08 / CA-09: Pipeline ficha_estudo com APIs reais (roda apenas em PR/CI explícito).

Requer: ANTHROPIC_API_KEY válida + acesso à internet.
Rodar localmente: pytest tests/e2e/test_ca08_exercicios.py -m real_api
"""
import os
import pytest

pytestmark = pytest.mark.real_api

if not os.environ.get("ANTHROPIC_API_KEY", "").startswith("sk-ant"):
    pytestmark = pytest.mark.skip(reason="ANTHROPIC_API_KEY não configurada")

_STATE = {
    "request_id": "ca08-e2e-001",
    "input": "desigualdade social no Brasil",
    "disciplina": "sociologia",
    "tipo": "ficha_estudo",
    "banca": None,
    "trecho": None,
    "fontes_autorizadas": [],
    "dados_coletados": {},
    "chunks_rag": [],
    "output": {},
    "tokens_used": 0,
    "cost_usd": 0.0,
    "session_id": "ca08-e2e-sess",
}


@pytest.mark.asyncio
class TestCA08Exercicios:
    """CA-08: ficha_estudo com 15 exercícios em distribuição 5/7/3."""

    async def test_ca08_retorna_15_exercicios(self):
        """CA-08: output deve conter exatamente 15 exercícios."""
        from graph import graph

        result = await graph.ainvoke({**_STATE, "request_id": "ca08-e2e-15"})
        output = result.get("output", {})

        if output.get("mensagem") == "Informação não localizada em fonte oficial":
            pytest.skip("Fontes externas indisponíveis — fallback CA-07 ativo")

        exercicios = output.get("exercicios", [])
        assert len(exercicios) == 15, f"CA-08: esperado 15 exercícios, obtido {len(exercicios)}"

    async def test_ca08_distribuicao_5_7_3(self):
        """CA-08: distribuição exatas/humanas/interdisciplinares deve ser 5/7/3."""
        from graph import graph

        result = await graph.ainvoke({**_STATE, "request_id": "ca08-e2e-dist"})
        output = result.get("output", {})

        if output.get("mensagem") == "Informação não localizada em fonte oficial":
            pytest.skip("Fontes externas indisponíveis — fallback CA-07 ativo")

        exercicios = output.get("exercicios", [])
        exatas = [e for e in exercicios if e.get("area") == "exatas"]
        humanas = [e for e in exercicios if e.get("area") == "humanas"]
        inter = [e for e in exercicios if e.get("area") == "interdisciplinar"]

        assert len(exatas) == 5, f"CA-08: esperado 5 exatas, obtido {len(exatas)}"
        assert len(humanas) == 7, f"CA-08: esperado 7 humanas, obtido {len(humanas)}"
        assert len(inter) == 3, f"CA-08: esperado 3 interdisciplinar, obtido {len(inter)}"

    async def test_ca09_sem_conceitos_duplicados(self):
        """CA-09: dois exercícios não podem cobrir o mesmo conceito central."""
        from graph import graph

        result = await graph.ainvoke({**_STATE, "request_id": "ca09-e2e-dup"})
        output = result.get("output", {})

        if output.get("mensagem") == "Informação não localizada em fonte oficial":
            pytest.skip("Fontes externas indisponíveis — fallback CA-07 ativo")

        exercicios = output.get("exercicios", [])
        conceitos = [e.get("conceito_central", "").lower() for e in exercicios]
        assert len(conceitos) == len(set(conceitos)), "CA-09: conceitos duplicados detectados"

    async def test_ca08_exatas_tem_resolucao(self):
        """CA-08: exercícios de exatas devem ter resolução passo a passo."""
        from graph import graph

        result = await graph.ainvoke({**_STATE, "request_id": "ca08-e2e-res"})
        output = result.get("output", {})

        if output.get("mensagem") == "Informação não localizada em fonte oficial":
            pytest.skip("Fontes externas indisponíveis — fallback CA-07 ativo")

        for ex in output.get("exercicios", []):
            if ex.get("area") == "exatas":
                resolucao = ex.get("resolucao", {})
                assert resolucao.get("passos"), f"CA-08: exercício exatas sem passos: {ex.get('conceito_central')}"
