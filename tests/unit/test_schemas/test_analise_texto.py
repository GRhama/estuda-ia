import pytest
from pydantic import ValidationError
from agents.schemas.analise_texto import RecursoEstilistico, AnaliseTextoModoA, AnaliseTextoModoB


class TestRecursoEstilistico:
    def test_cria_recurso(self):
        r = RecursoEstilistico(
            recurso="metáfora",
            trecho="a vida é uma viagem",
            efeito="aproxima conceitos abstratos de experiências concretas",
        )
        assert r.recurso == "metáfora"


class TestAnaliseTextoModoA:
    def test_modo_a_com_trecho(self):
        a = AnaliseTextoModoA(
            titulo_obra="Dom Casmurro",
            autor="Machado de Assis",
            recursos_estilisticos=[],
            temas=["ciúme", "memória", "traição"],
        )
        assert a.modo == "trecho"
        assert not hasattr(a, "limitacao")

    def test_modo_a_sem_titulo_ok(self):
        a = AnaliseTextoModoA(recursos_estilisticos=[], temas=["amor"])
        assert a.titulo_obra is None


class TestAnaliseTextoModoB:
    def test_modo_b_com_limitacao_ok(self):
        a = AnaliseTextoModoB(
            titulo_obra="Vidas Secas",
            autor="Graciliano Ramos",
            recursos_estilisticos=[],
            temas=["seca", "migração"],
            limitacao="Análise baseada em fontes secundárias — texto não fornecido.",
        )
        assert a.modo == "titulo_autor"
        assert a.limitacao

    def test_modo_b_sem_limitacao_levanta_erro(self):
        with pytest.raises(ValidationError) as exc_info:
            AnaliseTextoModoB(
                titulo_obra="Vidas Secas",
                autor="Graciliano Ramos",
                recursos_estilisticos=[],
                temas=[],
                limitacao="",
            )
        assert "limitacao" in str(exc_info.value)

    def test_modo_b_limitacao_espacos_levanta_erro(self):
        with pytest.raises(ValidationError):
            AnaliseTextoModoB(
                titulo_obra="Vidas Secas",
                autor="Graciliano Ramos",
                recursos_estilisticos=[],
                temas=[],
                limitacao="   ",
            )
