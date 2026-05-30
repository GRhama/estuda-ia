import asyncio
import httpx
from loguru import logger
from graph import GraphState
from core.data_fetcher import SOURCE_FETCHERS
from core.rss_fetcher import fetch_rss, RSS_SOURCES


async def run(state: GraphState) -> GraphState:
    """Coleta dados de todas as fontes autorizadas em paralelo."""
    rid = state["request_id"]
    fontes = state["fontes_autorizadas"]
    tema = state["input"]

    logger.debug(f"[{rid}] agent_dados: coletando {len(fontes)} fontes")

    async with httpx.AsyncClient() as client:
        tasks = [_fetch(client, rid, fonte, tema) for fonte in fontes]
        results = await asyncio.gather(*tasks, return_exceptions=True)

    dados: dict = {}
    for fonte, result in zip(fontes, results):
        if isinstance(result, Exception):
            logger.warning(f"[{rid}] fonte '{fonte}' exception: {type(result).__name__}")
        elif result:
            dados[fonte] = result

    logger.debug(f"[{rid}] agent_dados: {len(dados)}/{len(fontes)} fontes com dados")
    return {**state, "dados_coletados": dados}


async def _fetch(client: httpx.AsyncClient, rid: str, fonte: str, tema: str) -> dict | list:
    if fonte in RSS_SOURCES:
        loop = asyncio.get_event_loop()
        items = await loop.run_in_executor(None, fetch_rss, RSS_SOURCES[fonte], rid, tema)
        return items if items else {}
    fetcher = SOURCE_FETCHERS.get(fonte)
    if fetcher is None:
        logger.warning(f"[{rid}] fonte desconhecida: '{fonte}'")
        return {}
    return await fetcher(client, rid, tema)
