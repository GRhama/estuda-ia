import asyncio
from loguru import logger
from qdrant_client import AsyncQdrantClient
from qdrant_client.models import Distance, VectorParams, PointStruct
from graph import GraphState

_EMBED_MODEL = None
_RERANK_MODEL = None


def _get_embed_model():
    global _EMBED_MODEL
    if _EMBED_MODEL is None:
        from sentence_transformers import SentenceTransformer
        _EMBED_MODEL = SentenceTransformer("all-MiniLM-L6-v2")
    return _EMBED_MODEL


def _get_rerank_model():
    global _RERANK_MODEL
    if _RERANK_MODEL is None:
        from sentence_transformers import CrossEncoder
        _RERANK_MODEL = CrossEncoder("cross-encoder/ms-marco-MiniLM-L-6-v2")
    return _RERANK_MODEL


async def run(state: GraphState) -> GraphState:
    rid = state["request_id"]
    session_id = state["session_id"]
    dados = state["dados_coletados"]
    tema = state["input"]

    collection = f"sessao_{session_id}"
    client = AsyncQdrantClient(":memory:")

    try:
        embed = _get_embed_model()
        chunks = await _index(client, collection, dados, rid)
        if not chunks:
            logger.warning(f"[{rid}] agent_rag: sem dados para indexar")
            return {**state, "chunks_rag": []}

        top_chunks = await _search_and_rerank(client, collection, tema, chunks, rid)
        logger.debug(f"[{rid}] agent_rag: {len(top_chunks)} chunks entregues")
        return {**state, "chunks_rag": top_chunks}
    finally:
        await _cleanup(client, collection, rid)


async def _index(client: AsyncQdrantClient, collection: str, dados: dict, rid: str) -> list[dict]:
    embed = _get_embed_model()
    chunks: list[dict] = []

    for fonte_id, dado in dados.items():
        items = dado if isinstance(dado, list) else [dado]
        for item in items:
            if isinstance(item, dict) and item.get("dado"):
                chunks.append({
                    "texto": item["dado"][:2000],
                    "fonte": item.get("fonte", fonte_id),
                    "url": item.get("url", ""),
                    "is_rss": item.get("is_rss", False),
                    "aviso_rss": item.get("aviso_rss"),
                })

    if not chunks:
        return []

    textos = [c["texto"] for c in chunks]
    loop = asyncio.get_event_loop()
    vectors = await loop.run_in_executor(None, embed.encode, textos)

    dim = int(vectors[0].shape[0])
    await client.create_collection(
        collection_name=collection,
        vectors_config=VectorParams(size=dim, distance=Distance.COSINE),
    )
    points = [
        PointStruct(id=i, vector=v.tolist(), payload=chunks[i])
        for i, v in enumerate(vectors)
    ]
    await client.upsert(collection_name=collection, points=points)
    logger.debug(f"[{rid}] agent_rag: {len(chunks)} chunks indexados")
    return chunks


async def _search_and_rerank(
    client: AsyncQdrantClient, collection: str, query: str, chunks: list, rid: str
) -> list[dict]:
    embed = _get_embed_model()
    rerank = _get_rerank_model()
    loop = asyncio.get_event_loop()

    q_vecs = await loop.run_in_executor(None, embed.encode, [query])
    k = min(15, len(chunks))

    from qdrant_client.models import QueryRequest
    results = await client.query_points(
        collection_name=collection,
        query=q_vecs[0].tolist(),
        limit=k,
    )
    results = results.points
    if not results:
        return []

    pairs = [[query, r.payload["texto"]] for r in results]
    scores = await loop.run_in_executor(None, rerank.predict, pairs)

    ranked = sorted(zip(scores, results), key=lambda x: x[0], reverse=True)
    top3 = [r.payload for _, r in ranked[:3]]
    logger.debug(f"[{rid}] agent_rag: {k} candidatos → rerank → top {len(top3)}")
    return top3


async def _cleanup(client: AsyncQdrantClient, collection: str, rid: str) -> None:
    try:
        await client.delete_collection(collection_name=collection)
        logger.debug(f"[{rid}] agent_rag: coleção '{collection}' deletada (LGPD)")
    except Exception as e:
        logger.warning(f"[{rid}] agent_rag cleanup: {type(e).__name__}")
    finally:
        await client.close()
