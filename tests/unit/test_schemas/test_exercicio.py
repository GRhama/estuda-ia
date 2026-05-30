import pytest
from pydantic import ValidationError
from agents.schemas.exercicio import AlternativasQuestao, ResolucaoQuestao, ExercicioMultiplaEscolha


def _alt():
    return AlternativasQuestao(a="op A", b="op B", c="op C", d="op D", e="op E")


def _res_exatas():
    return ResolucaoQuestao(
        resposta_correta="a",
        explicacao="resolução detalhada",
        passo_a_passo=["passo 1: isolar variável", "passo 2: calcular"],
    )


def _res_humanas():
    return ResolucaoQuestao(
        resposta_correta="b",
        explicacao="contexto histórico",
        por_que_incorretas={"a": "fora do período", "c": "confunde conceitos", "d": "incorreto", "e": "errado"},
    )


class TestAlternativasQuestao:
    def test_cinco_alternativas(self):
        alt = _alt()
        assert alt.a == "op A"
        assert alt.e == "op E"


class TestResolucaoQuestao:
    @pytest.mark.parametrize("letra", ["a", "b", "c", "d", "e"])
    def test_letras_validas(self, letra):
        r = ResolucaoQuestao(resposta_correta=letra, explicacao="ok")
        assert r.resposta_correta == letra

    def test_letra_invalida_levanta_erro(self):
        with pytest.raises(ValidationError):
            ResolucaoQuestao(resposta_correta="f", explicacao="ok")


class TestExercicioMultiplaEscolha:
    def test_exatas_com_passo_a_passo_ok(self):
        e = ExercicioMultiplaEscolha(
            enunciado="calcule x na equação 2x = 4",
            alternativas=_alt(),
            resolucao=_res_exatas(),
            area="exatas",
            conceito="equações lineares",
        )
        assert e.area == "exatas"
        assert e.resolucao.passo_a_passo is not None

    def test_exatas_sem_passo_a_passo_levanta_erro(self):
        res = ResolucaoQuestao(resposta_correta="a", explicacao="ok")
        with pytest.raises(ValidationError) as exc_info:
            ExercicioMultiplaEscolha(
                enunciado="calcule x",
                alternativas=_alt(),
                resolucao=res,
                area="exatas",
                conceito="equações",
            )
        assert "passo_a_passo" in str(exc_info.value)

    def test_humanas_com_por_que_incorretas_ok(self):
        e = ExercicioMultiplaEscolha(
            enunciado="qual o contexto da Revolução Francesa?",
            alternativas=_alt(),
            resolucao=_res_humanas(),
            area="humanas",
            conceito="revolução francesa",
        )
        assert e.area == "humanas"
        assert e.resolucao.por_que_incorretas is not None

    def test_humanas_sem_por_que_incorretas_levanta_erro(self):
        res = ResolucaoQuestao(resposta_correta="b", explicacao="ok")
        with pytest.raises(ValidationError) as exc_info:
            ExercicioMultiplaEscolha(
                enunciado="qual o contexto?",
                alternativas=_alt(),
                resolucao=res,
                area="humanas",
                conceito="revolução",
            )
        assert "por_que_incorretas" in str(exc_info.value)

    def test_linguagens_sem_restricao_extra_ok(self):
        res = ResolucaoQuestao(resposta_correta="c", explicacao="ok")
        e = ExercicioMultiplaEscolha(
            enunciado="identifique o recurso estilístico",
            alternativas=_alt(),
            resolucao=res,
            area="linguagens",
            conceito="metáfora",
        )
        assert e.area == "linguagens"
