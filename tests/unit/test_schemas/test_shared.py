import pytest
from pydantic import ValidationError
from agents.schemas.shared import FonteOficial, BancaRelevancia, FontePublica


class TestFonteOficial:
    def test_cria_sem_rss(self):
        f = FonteOficial(fonte="IBGE", url="https://ibge.gov.br/dado")
        assert f.fonte == "IBGE"
        assert not f.is_rss
        assert f.aviso_rss is None

    def test_cria_com_rss_e_aviso(self):
        f = FonteOficial(
            fonte="Senado RSS",
            url="https://senado.leg.br/feed",
            is_rss=True,
            aviso_rss="Dados RSS — verificar data de publicação",
        )
        assert f.is_rss
        assert f.aviso_rss is not None

    def test_rss_sem_aviso_levanta_validation_error(self):
        with pytest.raises(ValidationError) as exc_info:
            FonteOficial(
                fonte="Senado RSS",
                url="https://senado.leg.br/feed",
                is_rss=True,
            )
        assert "aviso_rss" in str(exc_info.value)

    def test_trecho_opcional(self):
        f = FonteOficial(fonte="IBGE", url="https://ibge.gov.br", trecho="população 2022: 214M")
        assert f.trecho == "população 2022: 214M"

    def test_nao_rss_sem_aviso_ok(self):
        f = FonteOficial(fonte="IBGE API", url="https://servicodados.ibge.gov.br/api")
        assert f.aviso_rss is None
        assert not f.is_rss


class TestBancaRelevancia:
    @pytest.mark.parametrize("banca", ["ENEM", "FUVEST", "UNESP", "UNICAMP"])
    def test_bancas_aceitas(self, banca):
        b = BancaRelevancia(banca=banca, relevante=True, justificativa="tema recorrente")
        assert b.banca == banca

    def test_banca_invalida_levanta_erro(self):
        with pytest.raises(ValidationError):
            BancaRelevancia(banca="FGTS", relevante=True, justificativa="inválida")

    def test_relevante_false(self):
        b = BancaRelevancia(banca="UNESP", relevante=False, justificativa="fora do escopo")
        assert b.relevante is False


class TestFontePublica:
    def test_cria_fonte_publica_minima(self):
        fp = FontePublica(fonte="IBGE", url="https://ibge.gov.br")
        assert fp.fonte == "IBGE"
        assert fp.trecho is None

    def test_cria_com_trecho(self):
        fp = FontePublica(fonte="IBGE", url="https://ibge.gov.br", trecho="dado relevante")
        assert fp.trecho == "dado relevante"
