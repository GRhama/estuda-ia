import pytest
from agents.schemas.resumo import Resumo


class TestResumo:
    def test_resumo_ok(self):
        r = Resumo(
            titulo="A Revolução Industrial",
            topicos=["origens", "consequências", "impacto social"],
            texto_resumido="A Revolução Industrial transformou...",
        )
        assert r.titulo == "A Revolução Industrial"
        assert len(r.topicos) == 3
        assert r.fontes == []
