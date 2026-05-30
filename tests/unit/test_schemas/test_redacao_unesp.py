import pytest
from agents.schemas.redacao_unesp import RedacaoUNESP


class TestRedacaoUNESP:
    def test_redacao_basica_ok(self):
        r = RedacaoUNESP(
            tipo_texto="dissertativo",
            introducao="Introdução...",
            desenvolvimento=["Argumento..."],
            conclusao="Conclusão...",
        )
        assert r.tipo_texto == "dissertativo"
        assert r.fontes == []
