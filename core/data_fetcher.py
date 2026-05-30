import httpx
from loguru import logger
from core.sanitizer import check_ssrf, sanitize_api_output

_TIMEOUT = httpx.Timeout(10.0)


async def safe_fetch(client: httpx.AsyncClient, url: str, **kwargs) -> httpx.Response:
    """SSRF-safe GET. follow_redirects sempre False."""
    check_ssrf(url)
    return await client.get(url, timeout=_TIMEOUT, follow_redirects=False, **kwargs)


def _ok(dado: str, fonte: str, url: str) -> dict:
    return {"dado": sanitize_api_output(dado), "fonte": fonte, "url": url}


async def fetch_ibge(client: httpx.AsyncClient, rid: str, tema: str) -> dict:
    url = (
        "https://servicodados.ibge.gov.br/api/v3/agregados/5938/periodos/-4"
        "/variaveis/37?localidades=N1[all]"
    )
    try:
        r = await safe_fetch(client, url)
        r.raise_for_status()
        return _ok(r.text, "IBGE SIDRA", url)
    except Exception as e:
        logger.warning(f"[{rid}] ibge falhou: {type(e).__name__}")
        return {}


async def fetch_ipea(client: httpx.AsyncClient, rid: str, tema: str) -> dict:
    url = "https://ipeadata.gov.br/api/odata4/ValoresSerie(SERCODIGO='PIB_IBGE')"
    try:
        r = await safe_fetch(client, url)
        r.raise_for_status()
        return _ok(r.text, "IPEA Data", url)
    except Exception as e:
        logger.warning(f"[{rid}] ipea falhou: {type(e).__name__}")
        return {}


async def fetch_worldbank(client: httpx.AsyncClient, rid: str, tema: str) -> dict:
    url = "https://api.worldbank.org/v2/country/BR/indicator/NY.GDP.PCAP.CD?format=json&mrv=5"
    try:
        r = await safe_fetch(client, url)
        r.raise_for_status()
        return _ok(r.text, "World Bank", url)
    except Exception as e:
        logger.warning(f"[{rid}] worldbank falhou: {type(e).__name__}")
        return {}


async def fetch_inpe(client: httpx.AsyncClient, rid: str, tema: str) -> dict:
    url = "https://terrabrasilis.dpi.inpe.br/geoserver/prodes-amazon/ows?service=WFS&version=2.0.0&request=GetPropertyValue&typeNames=prodes-amazon:annual_deforestation&valueReference=year&outputFormat=json"
    try:
        r = await safe_fetch(client, url)
        r.raise_for_status()
        return _ok(r.text, "INPE TerraMA²", url)
    except Exception as e:
        logger.warning(f"[{rid}] inpe falhou: {type(e).__name__}")
        return {}


async def fetch_paho(client: httpx.AsyncClient, rid: str, tema: str) -> dict:
    import urllib.parse
    query = urllib.parse.quote(tema)
    url = f"https://paho.org/en/documents?search={query}"
    try:
        r = await safe_fetch(client, url)
        r.raise_for_status()
        return _ok(r.text, "OMS/PAHO", url)
    except Exception as e:
        logger.warning(f"[{rid}] paho falhou: {type(e).__name__}")
        return {}


async def fetch_lexml(client: httpx.AsyncClient, rid: str, tema: str) -> dict:
    import urllib.parse
    query = urllib.parse.quote(tema)
    url = f"https://lexml.gov.br/urn/urn:lex:br:federal:lei:2023;?busca={query}"
    try:
        r = await safe_fetch(client, url)
        r.raise_for_status()
        return _ok(r.text, "LexML", url)
    except Exception as e:
        logger.warning(f"[{rid}] lexml falhou: {type(e).__name__}")
        return {}


async def fetch_restcountries(client: httpx.AsyncClient, rid: str, tema: str) -> dict:
    url = "https://restcountries.com/v3.1/alpha/BR"
    try:
        r = await safe_fetch(client, url)
        r.raise_for_status()
        return _ok(r.text, "REST Countries", url)
    except Exception as e:
        logger.warning(f"[{rid}] restcountries falhou: {type(e).__name__}")
        return {}


async def fetch_unesco(client: httpx.AsyncClient, rid: str, tema: str) -> dict:
    url = "https://whc.unesco.org/en/list/xml/"
    try:
        r = await safe_fetch(client, url)
        r.raise_for_status()
        return _ok(r.text, "UNESCO WHC", url)
    except Exception as e:
        logger.warning(f"[{rid}] unesco falhou: {type(e).__name__}")
        return {}


async def fetch_wikidata(client: httpx.AsyncClient, rid: str, tema: str) -> dict:
    import urllib.parse
    sparql = f"""
    SELECT ?item ?itemLabel ?description WHERE {{
      ?item wdt:P17 wd:Q155 .
      ?item rdfs:label "{tema}"@pt .
      OPTIONAL {{ ?item schema:description ?description . FILTER(LANG(?description)="pt") }}
      SERVICE wikibase:label {{ bd:serviceParam wikibase:language "pt,en". }}
    }} LIMIT 5
    """
    url = "https://query.wikidata.org/sparql?query=" + urllib.parse.quote(sparql) + "&format=json"
    try:
        r = await safe_fetch(client, url, headers={"Accept": "application/sparql-results+json"})
        r.raise_for_status()
        return _ok(r.text, "Wikidata", url)
    except Exception as e:
        logger.warning(f"[{rid}] wikidata falhou: {type(e).__name__}")
        return {}


async def fetch_fao(client: httpx.AsyncClient, rid: str, tema: str) -> dict:
    url = "https://fenix.fao.org/faostat/api/v1/en/data/QCL?area=21&element=5510&item=2511&year=2022&output_type=objects"
    try:
        r = await safe_fetch(client, url)
        r.raise_for_status()
        return _ok(r.text, "FAO FAOSTAT", url)
    except Exception as e:
        logger.warning(f"[{rid}] fao falhou: {type(e).__name__}")
        return {}


async def fetch_onu(client: httpx.AsyncClient, rid: str, tema: str) -> dict:
    import urllib.parse
    query = urllib.parse.quote(tema)
    url = f"https://documents.un.org/api/search?query={query}&limit=5"
    try:
        r = await safe_fetch(client, url)
        r.raise_for_status()
        return _ok(r.text, "ONU Documents", url)
    except Exception as e:
        logger.warning(f"[{rid}] onu falhou: {type(e).__name__}")
        return {}


async def fetch_wikipedia_pt(client: httpx.AsyncClient, rid: str, tema: str) -> dict:
    import urllib.parse
    url = (
        "https://pt.wikipedia.org/w/api.php?action=query&prop=extracts"
        f"&exintro=1&explaintext=1&titles={urllib.parse.quote(tema)}&format=json"
    )
    try:
        r = await safe_fetch(client, url)
        r.raise_for_status()
        return _ok(r.text, "Wikipedia PT", url)
    except Exception as e:
        logger.warning(f"[{rid}] wikipedia_pt falhou: {type(e).__name__}")
        return {}


async def fetch_wikipedia_en(client: httpx.AsyncClient, rid: str, tema: str) -> dict:
    import urllib.parse
    url = (
        "https://en.wikipedia.org/w/api.php?action=query&prop=extracts"
        f"&exintro=1&explaintext=1&titles={urllib.parse.quote(tema)}&format=json"
    )
    try:
        r = await safe_fetch(client, url)
        r.raise_for_status()
        return _ok(r.text, "Wikipedia EN", url)
    except Exception as e:
        logger.warning(f"[{rid}] wikipedia_en falhou: {type(e).__name__}")
        return {}


async def fetch_openalex(client: httpx.AsyncClient, rid: str, tema: str) -> dict:
    import urllib.parse
    url = f"https://api.openalex.org/works?search={urllib.parse.quote(tema)}&filter=institutions.country_code:BR&per_page=5"
    try:
        r = await safe_fetch(client, url)
        r.raise_for_status()
        return _ok(r.text, "OpenAlex", url)
    except Exception as e:
        logger.warning(f"[{rid}] openalex falhou: {type(e).__name__}")
        return {}


async def fetch_scielo(client: httpx.AsyncClient, rid: str, tema: str) -> dict:
    import urllib.parse
    url = f"https://scielo.br/cgi-bin/wxis.exe/iah/?IsisScript=iah/iah.xis&base=article^dlibrary&format=iso.pft&lang=p&nextAction=lnk&indexSearch=TW&exprSearch={urllib.parse.quote(tema)}"
    try:
        r = await safe_fetch(client, url)
        r.raise_for_status()
        return _ok(r.text, "SciELO", url)
    except Exception as e:
        logger.warning(f"[{rid}] scielo falhou: {type(e).__name__}")
        return {}


async def fetch_pubmed(client: httpx.AsyncClient, rid: str, tema: str) -> dict:
    import urllib.parse
    search_url = f"https://eutils.ncbi.nlm.nih.gov/entrez/eutils/esearch.fcgi?db=pubmed&term={urllib.parse.quote(tema)}+Brazil&retmax=5&retmode=json"
    try:
        r = await safe_fetch(client, search_url)
        r.raise_for_status()
        return _ok(r.text, "PubMed/NCBI", search_url)
    except Exception as e:
        logger.warning(f"[{rid}] pubmed falhou: {type(e).__name__}")
        return {}


async def fetch_gutendex(client: httpx.AsyncClient, rid: str, tema: str) -> dict:
    import urllib.parse
    url = f"https://gutendex.com/books?search={urllib.parse.quote(tema)}&languages=pt"
    try:
        r = await safe_fetch(client, url)
        r.raise_for_status()
        return _ok(r.text, "Gutendex/Gutenberg", url)
    except Exception as e:
        logger.warning(f"[{rid}] gutendex falhou: {type(e).__name__}")
        return {}


async def fetch_dominio_publico(client: httpx.AsyncClient, rid: str, tema: str) -> dict:
    import urllib.parse
    url = f"https://www.dominiopublico.gov.br/pesquisa/ResultadoPesquisaObraForm.do?first=0&skip=0&ds_titulo={urllib.parse.quote(tema)}&co_midia=2"
    try:
        r = await safe_fetch(client, url)
        r.raise_for_status()
        return _ok(r.text, "Domínio Público MEC", url)
    except Exception as e:
        logger.warning(f"[{rid}] dominio_publico falhou: {type(e).__name__}")
        return {}


async def fetch_rss_senado(client: httpx.AsyncClient, rid: str, tema: str) -> dict:
    import asyncio
    from core.rss_fetcher import fetch_rss, RSS_SOURCES
    loop = asyncio.get_event_loop()
    items = await loop.run_in_executor(None, fetch_rss, RSS_SOURCES["senado"], rid, tema)
    if not items:
        return {}
    return {"dado": str(items[:3]), "fonte": "Senado RSS", "url": RSS_SOURCES["senado"]}


async def fetch_rss_gov_br(client: httpx.AsyncClient, rid: str, tema: str) -> dict:
    import asyncio
    from core.rss_fetcher import fetch_rss, RSS_SOURCES
    loop = asyncio.get_event_loop()
    items = await loop.run_in_executor(None, fetch_rss, RSS_SOURCES["gov_br"], rid, tema)
    if not items:
        return {}
    return {"dado": str(items[:3]), "fonte": "Gov.br RSS", "url": RSS_SOURCES["gov_br"]}


SOURCE_FETCHERS = {
    "ibge": fetch_ibge,
    "ipea": fetch_ipea,
    "worldbank": fetch_worldbank,
    "inpe": fetch_inpe,
    "paho": fetch_paho,
    "lexml": fetch_lexml,
    "restcountries": fetch_restcountries,
    "unesco": fetch_unesco,
    "wikidata": fetch_wikidata,
    "fao": fetch_fao,
    "onu": fetch_onu,
    "wikipedia_pt": fetch_wikipedia_pt,
    "wikipedia_en": fetch_wikipedia_en,
    "openalex": fetch_openalex,
    "scielo": fetch_scielo,
    "pubmed": fetch_pubmed,
    "gutenberg": fetch_gutendex,
    "gutendex": fetch_gutendex,
    "dominio_publico": fetch_dominio_publico,
    "senado": fetch_rss_senado,
    "gov_br": fetch_rss_gov_br,
}
