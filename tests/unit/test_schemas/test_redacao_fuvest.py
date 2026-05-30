import pytest
from agents.schemas.redacao_fuvest import RedacaoFUVEST


class TestRedacaoFUVEST:
    def test_redacao_basica_ok(self):
        r = RedacaoFUVEST(
            tipo_texto="dissertativo-argumentativo",
            introducao="Introdução...",
            desenvolvimento=["Argumento 1...", "Argumento 2..."],
            conclusao="Conclusão...",
        )
        assert r.tipo_texto == "dissertativo-argumentativo"
        assert r.titulo is None
        assert r.fontes == []

    def test_com_titulo(self):
        r = RedacaoFUVEST(
            tipo_texto="narrativo",
            titulo="O Encontro",
            introducao="Era uma vez...",
            desenvolvimento=["..."],
            conclusao="Fim.",
        )
        assert r.titulo == "O Encontro"
