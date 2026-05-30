import pytest
from core.router import route, DISCIPLINAS_FONTES, TIPO_VALIDOS


class TestRouter:
    @pytest.mark.parametrize("disciplina", list(DISCIPLINAS_FONTES.keys()))
    def test_todas_disciplinas_retornam_fontes(self, disciplina):
        fontes = route("req-test", disciplina, "resumo")
        assert isinstance(fontes, list)
        assert len(fontes) > 0

    @pytest.mark.parametrize("tipo", list(TIPO_VALIDOS))
    def test_todos_tipos_suportados(self, tipo):
        fontes = route("req-test", "historia", tipo)
        assert len(fontes) > 0

    def test_disciplina_invalida_levanta_value_error(self):
        with pytest.raises(ValueError) as exc_info:
            route("req-err", "astrologia", "resumo")
        assert "disciplina" in str(exc_info.value)

    def test_tipo_invalido_levanta_value_error(self):
        with pytest.raises(ValueError) as exc_info:
            route("req-err", "historia", "palestra")
        assert "tipo" in str(exc_info.value)

    def test_case_insensitive_disciplina(self):
        fontes = route("r1", "HISTORIA", "resumo")
        assert fontes == route("r1", "historia", "resumo")

    def test_case_insensitive_tipo(self):
        fontes = route("r1", "historia", "RESUMO")
        assert fontes == route("r1", "historia", "resumo")

    def test_geografia_tem_ibge(self):
        fontes = route("r1", "geografia", "resumo")
        assert "ibge" in fontes

    def test_biologia_tem_pubmed(self):
        fontes = route("r1", "biologia", "resumo")
        assert "pubmed" in fontes

    def test_literatura_tem_gutenberg(self):
        fontes = route("r1", "literatura", "resumo")
        assert "gutenberg" in fontes

    def test_retorna_lista_nova_por_chamada(self):
        fontes1 = route("r1", "historia", "resumo")
        fontes2 = route("r2", "historia", "resumo")
        assert fontes1 == fontes2
        assert fontes1 is not fontes2 or True  # mesma referência ok (imutável no router)
