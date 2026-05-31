"""Testes de integração — 19 fontes mockadas com respx."""
import re
import pytest
import httpx
import respx
from core.data_fetcher import (
    safe_fetch,
    fetch_ibge, fetch_ipea, fetch_worldbank, fetch_inpe, fetch_paho,
    fetch_lexml, fetch_restcountries, fetch_unesco, fetch_wikidata,
    fetch_fao, fetch_onu, fetch_wikipedia_pt, fetch_wikipedia_en,
    fetch_openalex, fetch_scielo, fetch_pubmed, fetch_gutendex,
    fetch_dominio_publico, fetch_rss_senado, fetch_rss_gov_br,
    SOURCE_FETCHERS,
)

RID = "test-integration-001"
TEMA = "desigualdade social"
_TEXT = "dado mockado"


def _pat(hostname: str):
    return re.compile(rf"https?://{re.escape(hostname)}")


@pytest.mark.asyncio
class TestSafeFetch:
    @respx.mock
    async def test_retorna_response_200(self):
        respx.get(_pat("servicodados.ibge.gov.br")).mock(
            return_value=httpx.Response(200, text=_TEXT)
        )
        async with httpx.AsyncClient() as c:
            r = await safe_fetch(c, "https://servicodados.ibge.gov.br/api/test")
        assert r.status_code == 200

    @respx.mock
    async def test_nao_segue_redirect(self):
        respx.get(_pat("servicodados.ibge.gov.br")).mock(
            return_value=httpx.Response(301, headers={"Location": "https://evil.com"})
        )
        async with httpx.AsyncClient() as c:
            r = await safe_fetch(c, "https://servicodados.ibge.gov.br/api/redir")
        assert r.status_code == 301

    async def test_host_nao_autorizado_levanta_ssrf(self):
        async with httpx.AsyncClient() as c:
            with pytest.raises(ValueError, match="SSRF"):
                await safe_fetch(c, "https://evil.com/steal")


@pytest.mark.asyncio
class TestFetchIBGE:
    @respx.mock
    async def test_retorna_dado_fonte_url(self):
        respx.get(_pat("servicodados.ibge.gov.br")).mock(
            return_value=httpx.Response(200, text=_TEXT)
        )
        async with httpx.AsyncClient() as c:
            r = await fetch_ibge(c, RID, TEMA)
        assert r["fonte"] == "IBGE SIDRA"
        assert r["dado"] == _TEXT
        assert "servicodados.ibge.gov.br" in r["url"]

    @respx.mock
    async def test_erro_http_retorna_vazio(self):
        respx.get(_pat("servicodados.ibge.gov.br")).mock(
            return_value=httpx.Response(500)
        )
        async with httpx.AsyncClient() as c:
            r = await fetch_ibge(c, RID, TEMA)
        assert r == {}

    @respx.mock
    async def test_timeout_retorna_vazio(self):
        respx.get(_pat("servicodados.ibge.gov.br")).mock(
            side_effect=httpx.TimeoutException("timeout")
        )
        async with httpx.AsyncClient() as c:
            r = await fetch_ibge(c, RID, TEMA)
        assert r == {}


@pytest.mark.asyncio
class TestFetchIPEA:
    @respx.mock
    async def test_retorna_dado(self):
        respx.get(_pat("ipeadata.gov.br")).mock(
            return_value=httpx.Response(200, text=_TEXT)
        )
        async with httpx.AsyncClient() as c:
            r = await fetch_ipea(c, RID, TEMA)
        assert r["fonte"] == "IPEA Data"

    @respx.mock
    async def test_timeout_retorna_vazio(self):
        respx.get(_pat("ipeadata.gov.br")).mock(
            side_effect=httpx.TimeoutException("timeout")
        )
        async with httpx.AsyncClient() as c:
            r = await fetch_ipea(c, RID, TEMA)
        assert r == {}


@pytest.mark.asyncio
class TestFetchWorldBank:
    @respx.mock
    async def test_retorna_dado(self):
        respx.get(_pat("api.worldbank.org")).mock(
            return_value=httpx.Response(200, text=_TEXT)
        )
        async with httpx.AsyncClient() as c:
            r = await fetch_worldbank(c, RID, TEMA)
        assert r["fonte"] == "World Bank"


@pytest.mark.asyncio
class TestFetchINPE:
    @respx.mock
    async def test_retorna_dado(self):
        respx.get(_pat("terrabrasilis.dpi.inpe.br")).mock(
            return_value=httpx.Response(200, text=_TEXT)
        )
        async with httpx.AsyncClient() as c:
            r = await fetch_inpe(c, RID, TEMA)
        assert r["fonte"] == "INPE TerraMA²"


@pytest.mark.asyncio
class TestFetchPAHO:
    @respx.mock
    async def test_retorna_dado(self):
        respx.get(_pat("paho.org")).mock(
            return_value=httpx.Response(200, text=_TEXT)
        )
        async with httpx.AsyncClient() as c:
            r = await fetch_paho(c, RID, TEMA)
        assert r["fonte"] == "OMS/PAHO"


@pytest.mark.asyncio
class TestFetchLexML:
    @respx.mock
    async def test_retorna_dado(self):
        respx.get(_pat("lexml.gov.br")).mock(
            return_value=httpx.Response(200, text=_TEXT)
        )
        async with httpx.AsyncClient() as c:
            r = await fetch_lexml(c, RID, TEMA)
        assert r["fonte"] == "LexML"


@pytest.mark.asyncio
class TestFetchRestCountries:
    @respx.mock
    async def test_retorna_dado(self):
        respx.get(_pat("restcountries.com")).mock(
            return_value=httpx.Response(200, text=_TEXT)
        )
        async with httpx.AsyncClient() as c:
            r = await fetch_restcountries(c, RID, TEMA)
        assert r["fonte"] == "REST Countries"


@pytest.mark.asyncio
class TestFetchUNESCO:
    @respx.mock
    async def test_retorna_dado(self):
        respx.get(_pat("whc.unesco.org")).mock(
            return_value=httpx.Response(200, text=_TEXT)
        )
        async with httpx.AsyncClient() as c:
            r = await fetch_unesco(c, RID, TEMA)
        assert r["fonte"] == "UNESCO WHC"


@pytest.mark.asyncio
class TestFetchWikidata:
    @respx.mock
    async def test_retorna_dado(self):
        respx.get(_pat("query.wikidata.org")).mock(
            return_value=httpx.Response(200, text=_TEXT)
        )
        async with httpx.AsyncClient() as c:
            r = await fetch_wikidata(c, RID, TEMA)
        assert r["fonte"] == "Wikidata"


@pytest.mark.asyncio
class TestFetchFAO:
    @respx.mock
    async def test_retorna_dado(self):
        respx.get(_pat("fenix.fao.org")).mock(
            return_value=httpx.Response(200, text=_TEXT)
        )
        async with httpx.AsyncClient() as c:
            r = await fetch_fao(c, RID, TEMA)
        assert r["fonte"] == "FAO FAOSTAT"


@pytest.mark.asyncio
class TestFetchONU:
    @respx.mock
    async def test_retorna_dado(self):
        respx.get(_pat("documents.un.org")).mock(
            return_value=httpx.Response(200, text=_TEXT)
        )
        async with httpx.AsyncClient() as c:
            r = await fetch_onu(c, RID, TEMA)
        assert r["fonte"] == "ONU Documents"


@pytest.mark.asyncio
class TestFetchWikipediaPT:
    @respx.mock
    async def test_retorna_dado(self):
        # Two-step: search returns pageid, extract returns text
        search_resp = httpx.Response(
            200, json={"query": {"search": [{"pageid": 123, "title": "Desigualdade social"}]}}
        )
        extract_resp = httpx.Response(200, text=_TEXT)
        respx.get(_pat("pt.wikipedia.org")).mock(side_effect=[search_resp, extract_resp])
        async with httpx.AsyncClient() as c:
            r = await fetch_wikipedia_pt(c, RID, TEMA)
        assert r["fonte"] == "Wikipedia PT"


@pytest.mark.asyncio
class TestFetchWikipediaEN:
    @respx.mock
    async def test_retorna_dado(self):
        respx.get(_pat("en.wikipedia.org")).mock(
            return_value=httpx.Response(200, text=_TEXT)
        )
        async with httpx.AsyncClient() as c:
            r = await fetch_wikipedia_en(c, RID, TEMA)
        assert r["fonte"] == "Wikipedia EN"


@pytest.mark.asyncio
class TestFetchOpenAlex:
    @respx.mock
    async def test_retorna_dado(self):
        respx.get(_pat("api.openalex.org")).mock(
            return_value=httpx.Response(200, text=_TEXT)
        )
        async with httpx.AsyncClient() as c:
            r = await fetch_openalex(c, RID, TEMA)
        assert r["fonte"] == "OpenAlex"


@pytest.mark.asyncio
class TestFetchSciELO:
    @respx.mock
    async def test_retorna_dado(self):
        respx.get(_pat("scielo.br")).mock(
            return_value=httpx.Response(200, text=_TEXT)
        )
        async with httpx.AsyncClient() as c:
            r = await fetch_scielo(c, RID, TEMA)
        assert r["fonte"] == "SciELO"


@pytest.mark.asyncio
class TestFetchPubMed:
    @respx.mock
    async def test_retorna_dado(self):
        respx.get(_pat("eutils.ncbi.nlm.nih.gov")).mock(
            return_value=httpx.Response(200, text=_TEXT)
        )
        async with httpx.AsyncClient() as c:
            r = await fetch_pubmed(c, RID, TEMA)
        assert r["fonte"] == "PubMed/NCBI"


@pytest.mark.asyncio
class TestFetchGutendex:
    @respx.mock
    async def test_retorna_dado(self):
        respx.get(_pat("gutendex.com")).mock(
            return_value=httpx.Response(200, text=_TEXT)
        )
        async with httpx.AsyncClient() as c:
            r = await fetch_gutendex(c, RID, TEMA)
        assert r["fonte"] == "Gutendex/Gutenberg"


@pytest.mark.asyncio
class TestFetchDominioPublico:
    @respx.mock
    async def test_retorna_dado(self):
        respx.get(_pat("www.dominiopublico.gov.br")).mock(
            return_value=httpx.Response(200, text=_TEXT)
        )
        async with httpx.AsyncClient() as c:
            r = await fetch_dominio_publico(c, RID, TEMA)
        assert r["fonte"] == "Domínio Público MEC"


@pytest.mark.asyncio
class TestFetchRSSSenado:
    async def test_rss_erro_retorna_vazio(self, mocker):
        mocker.patch("core.rss_fetcher.fetch_rss", return_value=[])
        async with httpx.AsyncClient() as c:
            r = await fetch_rss_senado(c, RID, TEMA)
        assert r == {}

    async def test_rss_com_dados_retorna_dict(self, mocker):
        mocker.patch("core.rss_fetcher.fetch_rss", return_value=[
            {"dado": "notícia", "fonte": "Senado", "url": "https://senado.leg.br/n1",
             "is_rss": True, "aviso_rss": "aviso"}
        ])
        async with httpx.AsyncClient() as c:
            r = await fetch_rss_senado(c, RID, TEMA)
        assert r["fonte"] == "Senado RSS"


@pytest.mark.asyncio
class TestFetchRSSGovBr:
    async def test_rss_erro_retorna_vazio(self, mocker):
        mocker.patch("core.rss_fetcher.fetch_rss", return_value=[])
        async with httpx.AsyncClient() as c:
            r = await fetch_rss_gov_br(c, RID, TEMA)
        assert r == {}

    async def test_rss_com_dados_retorna_dict(self, mocker):
        mocker.patch("core.rss_fetcher.fetch_rss", return_value=[
            {"dado": "notícia gov", "fonte": "Gov.br", "url": "https://www.gov.br/n1",
             "is_rss": True, "aviso_rss": "aviso"}
        ])
        async with httpx.AsyncClient() as c:
            r = await fetch_rss_gov_br(c, RID, TEMA)
        assert r["fonte"] == "Gov.br RSS"


class TestSourceFetchersMap:
    def test_todas_fontes_do_router_tem_fetcher(self):
        from core.router import DISCIPLINAS_FONTES
        todas_fontes = {f for fontes in DISCIPLINAS_FONTES.values() for f in fontes}
        sem_fetcher = todas_fontes - set(SOURCE_FETCHERS)
        assert sem_fetcher == set(), f"Fontes sem fetcher: {sem_fetcher}"
