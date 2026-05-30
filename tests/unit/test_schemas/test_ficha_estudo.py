import pytest
from pydantic import ValidationError
from agents.schemas.ficha_estudo import FichaEstudo
from agents.schemas.exercicio import AlternativasQuestao, ExercicioMultiplaEscolha, ResolucaoQuestao


def _alt():
    return AlternativasQuestao(a="A", b="B", c="C", d="D", e="E")


def _exercicio(area: str, conceito: str) -> ExercicioMultiplaEscolha:
    if area == "exatas":
        res = ResolucaoQuestao(resposta_correta="a", explicacao="ok", passo_a_passo=["p1"])
    elif area == "humanas":
        res = ResolucaoQuestao(resposta_correta="b", explicacao="ok", por_que_incorretas={"a": "e"})
    else:
        res = ResolucaoQuestao(resposta_correta="c", explicacao="ok")
    return ExercicioMultiplaEscolha(
        enunciado="questão", alternativas=_alt(), resolucao=res, area=area, conceito=conceito
    )


def _15_exercicios_corretos():
    exercicios = []
    for i in range(5):
        exercicios.append(_exercicio("exatas", f"exatas_{i}"))
    for i in range(7):
        exercicios.append(_exercicio("humanas", f"humanas_{i}"))
    for i in range(3):
        exercicios.append(_exercicio("linguagens", f"ling_{i}"))
    return exercicios


class TestFichaEstudo:
    def test_distribuicao_5_7_3_ok(self):
        f = FichaEstudo(
            resumo="resumo do tema",
            pontos_chave=["ponto 1", "ponto 2"],
            exercicios=_15_exercicios_corretos(),
        )
        assert len(f.exercicios) == 15

    def test_distribuicao_incorreta_15_exercicios_levanta_erro(self):
        exercicios = []
        for i in range(15):
            exercicios.append(_exercicio("exatas", f"c_{i}"))
        with pytest.raises(ValidationError) as exc_info:
            FichaEstudo(resumo="ok", pontos_chave=[], exercicios=exercicios)
        err_str = str(exc_info.value)
        assert "Distribuição" in err_str or "5/7/3" in err_str

    def test_menos_de_15_sem_validar_distribuicao(self):
        f = FichaEstudo(
            resumo="ok",
            pontos_chave=[],
            exercicios=[_exercicio("linguagens", "metáfora")],
        )
        assert len(f.exercicios) == 1

    def test_zero_exercicios_ok(self):
        f = FichaEstudo(resumo="ok", pontos_chave=[], exercicios=[])
        assert f.exercicios == []
