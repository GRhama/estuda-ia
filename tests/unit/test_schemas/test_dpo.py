import pytest
from agents.schemas.dpo import BlocoArgumentativo, DPO, TEXTO_SEM_FONTE
from agents.schemas.shared import FonteOficial


def _fonte():
    return FonteOficial(fonte="IBGE", url="https://ibge.gov.br/dado")


class TestTextoSemFonte:
    def test_constante_correta(self):
        assert TEXTO_SEM_FONTE == "Informação não localizada em fonte oficial"


class TestBlocoArgumentativo:
    def test_dado_com_fonte_preservado(self):
        b = BlocoArgumentativo(
            argumento="A pobreza aumentou",
            dado_estatistico="42% da população",
            fonte=_fonte(),
            localizado_em_fonte_oficial=True,
        )
        assert b.dado_estatistico == "42% da população"

    def test_dado_sem_fonte_substituido_por_texto_padrao(self):
        b = BlocoArgumentativo(
            argumento="A pobreza aumentou",
            dado_estatistico="número qualquer inventado",
            localizado_em_fonte_oficial=False,
        )
        assert b.dado_estatistico == TEXTO_SEM_FONTE

    def test_sem_dado_estatistico_e_sem_fonte_ok(self):
        b = BlocoArgumentativo(
            argumento="argumento sem estatística",
            localizado_em_fonte_oficial=False,
        )
        assert b.dado_estatistico is None

    def test_localizado_true_sem_fonte_objeto_ok(self):
        b = BlocoArgumentativo(
            argumento="dado verificado",
            dado_estatistico="60%",
            localizado_em_fonte_oficial=True,
        )
        assert b.dado_estatistico == "60%"


class TestDPO:
    def test_dpo_ok(self):
        bloco = BlocoArgumentativo(
            argumento="desigualdade social",
            localizado_em_fonte_oficial=False,
        )
        d = DPO(
            tema="desigualdade",
            tese="a desigualdade é um problema estrutural",
            blocos=[bloco],
            conclusao="portanto é necessário agir",
        )
        assert d.tema == "desigualdade"
