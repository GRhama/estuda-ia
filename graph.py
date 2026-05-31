from typing import Optional, List
from typing_extensions import TypedDict
from langgraph.graph import StateGraph, END
from loguru import logger


class GraphState(TypedDict):
    request_id: str
    input: str
    disciplina: str
    tipo: str
    banca: Optional[str]
    trecho: Optional[str]          # texto para análise — Modo A se presente, Modo B se None
    fontes_autorizadas: List[str]
    dados_coletados: dict
    chunks_rag: List[dict]
    output: dict
    tokens_used: int
    cost_usd: float
    session_id: str


async def _router_node(state: GraphState) -> GraphState:
    from core.router import route
    rid = state["request_id"]
    logger.debug(f"[{rid}] graph: nó router")
    fontes = route(rid, state["disciplina"], state["tipo"])
    return {**state, "fontes_autorizadas": fontes}


async def _agent_dados_node(state: GraphState) -> GraphState:
    from agents.agent_dados import run
    return await run(state)


async def _agent_rag_node(state: GraphState) -> GraphState:
    from agents.agent_rag import run
    return await run(state)


async def _agent_redator_node(state: GraphState) -> GraphState:
    from agents.agent_redator import run
    return await run(state)


async def _agent_analista_node(state: GraphState) -> GraphState:
    from agents.agent_analista import run
    return await run(state)


async def _agent_exercicios_node(state: GraphState) -> GraphState:
    from agents.agent_exercicios import run
    return await run(state)


async def _fallback_node(state: GraphState) -> GraphState:
    rid = state["request_id"]
    logger.warning(f"[{rid}] graph: fallback — chunks_rag vazio, sem chamada ao LLM")
    return {**state, "output": {
        "mensagem": "Informação não localizada em fonte oficial",
        "fontes": [],
    }}


def _route_after_rag(state: GraphState) -> str:
    if not state.get("chunks_rag"):
        return "fallback"
    return "agent_analista" if state.get("tipo") == "analise_texto" else "agent_redator"


def _should_run_exercicios(state: GraphState) -> str:
    return "agent_exercicios" if state.get("tipo") == "ficha_estudo" else END


builder = StateGraph(GraphState)
builder.add_node("router", _router_node)
builder.add_node("agent_dados", _agent_dados_node)
builder.add_node("agent_rag", _agent_rag_node)
builder.add_node("agent_redator", _agent_redator_node)
builder.add_node("agent_analista", _agent_analista_node)
builder.add_node("agent_exercicios", _agent_exercicios_node)
builder.add_node("fallback", _fallback_node)

builder.set_entry_point("router")
builder.add_edge("router", "agent_dados")
builder.add_edge("agent_dados", "agent_rag")
builder.add_conditional_edges("agent_rag", _route_after_rag)
builder.add_edge("fallback", END)
builder.add_conditional_edges("agent_redator", _should_run_exercicios)
builder.add_conditional_edges("agent_analista", _should_run_exercicios)
builder.add_edge("agent_exercicios", END)

graph = builder.compile()
