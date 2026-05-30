import feedparser
from datetime import datetime, timedelta, timezone
from loguru import logger
from core.sanitizer import sanitize_api_output

_AVISO_RSS = "Conteúdo proveniente de feed RSS — verificar data e autoria antes de citar."
_JANELA_SEMANAS = 4


def _is_recente(entry) -> bool:
    """Retorna True se o item do RSS foi publicado nas últimas 4 semanas."""
    published = getattr(entry, "published_parsed", None)
    if not published:
        return True  # sem data → não filtra
    dt = datetime(*published[:6], tzinfo=timezone.utc)
    return dt >= datetime.now(tz=timezone.utc) - timedelta(weeks=_JANELA_SEMANAS)


def fetch_rss(url: str, rid: str, keyword: str = "") -> list[dict]:
    """
    Parseia um feed RSS e retorna itens recentes com keyword no título/sumário.
    Retorna lista de {dado, fonte, url, is_rss, aviso_rss}.
    Falha silenciosa → [].
    """
    try:
        feed = feedparser.parse(url)
        if feed.bozo and not feed.entries:
            logger.warning(f"[{rid}] rss_fetcher: feed inválido {url}")
            return []

        nome_feed = feed.feed.get("title", url)
        resultado = []
        kw = keyword.lower()

        for entry in feed.entries:
            if not _is_recente(entry):
                continue
            titulo = entry.get("title", "")
            sumario = entry.get("summary", "")
            if kw and kw not in titulo.lower() and kw not in sumario.lower():
                continue
            dado = sanitize_api_output(f"{titulo}\n{sumario}")
            resultado.append({
                "dado": dado,
                "fonte": nome_feed,
                "url": entry.get("link", url),
                "is_rss": True,
                "aviso_rss": _AVISO_RSS,
            })

        logger.debug(f"[{rid}] rss_fetcher: {len(resultado)} itens de {url}")
        return resultado

    except Exception as e:
        logger.warning(f"[{rid}] rss_fetcher falhou ({url}): {type(e).__name__}")
        return []


RSS_SOURCES = {
    "senado": "https://www12.senado.leg.br/noticias/feed",
    "gov_br": "https://www.gov.br/pt-br/noticias/noticias.rss",
}
