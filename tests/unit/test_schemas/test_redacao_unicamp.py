import pytest
from agents.schemas.redacao_unicamp import PropostaUNICAMP, RedacaoUNICAMP


class TestPropostaUNICAMP:
    def test_carta_completa_adequada(self):
        p = PropostaUNICAMP(
            genero_textual="carta aberta",
            tem_vocalivo=True,
            tem_despedida=True,
            adequacao_genero=True,
        )
        assert p.adequacao_genero is True

    def test_sem_vocalivo_forca_adequacao_false(self):
        p = PropostaUNICAMP(
            genero_textual="carta",
            tem_vocalivo=False,
            tem_despedida=True,
            adequacao_genero=True,
        )
        assert p.adequacao_genero is False

    def test_sem_despedida_forca_adequacao_false(self):
        p = PropostaUNICAMP(
            genero_textual="carta",
            tem_vocalivo=True,
            tem_despedida=False,
            adequacao_genero=True,
        )
        assert p.adequacao_genero is False

    def test_sem_vocalivo_nem_despedida_adequacao_false(self):
        p = PropostaUNICAMP(
            genero_textual="carta",
            tem_vocalivo=False,
            tem_despedida=False,
            adequacao_genero=True,
        )
        assert p.adequacao_genero is False

    def test_adequacao_false_explicitamente_nao_override(self):
        p = PropostaUNICAMP(
            genero_textual="artigo",
            tem_vocalivo=True,
            tem_despedida=True,
            adequacao_genero=False,
        )
        assert p.adequacao_genero is False
