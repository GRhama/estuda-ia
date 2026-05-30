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
    fontes_autorizadas: List[str]
    dados_coletados: dict
    chunks_rag: List[dict]
    output: dict
    tokens_used: int
    cost_usd: float
    session_id: str


def _router_node(state: GraphState) -> GraphState:
    from core.router import route
    rid = state["request_id"]
    logger.debug(f"[{rid}] graph: nó router")
    fontes = route(rid, state["disciplina"], state["tipo"])
    return {**state, "fontes_autorizadas": fontes}


def _agent_dados_node(state: GraphState) -> GraphState:
    rid = state["request_id"]
    logger.debug(f"[{rid}] graph: nó agent_dados (stub Sprint 2)")
    return {**state, "dados_coletados": {}}


def _agent_rag_node(state: GraphState) -> GraphState:
    rid = state["request_id"]
    logger.debug(f"[{rid}] graph: nó agent_rag (stub Sprint 3)")
    return {**state, "chunks_rag": []}


def _agent_redator_node(state: GraphState) -> GraphState:
    rid = state["request_id"]
    logger.debug(f"[{rid}] graph: nó agent_redator (stub Sprint 3)")
    return {**state, "output": {}}


def _agent_exercicios_node(state: GraphState) -> GraphState:
    rid = state["request_id"]
    logger.debug(f"[{rid}] graph: nó agent_exercicios (stub Sprint 5)")
    return state


def _should_run_exercicios(state: GraphState) -> str:
    return "agent_exercicios" if state.get("tipo") == "ficha_estudo" else END


builder = StateGraph(GraphState)
builder.add_node("router", _router_node)
builder.add_node("agent_dados", _agent_dados_node)
builder.add_node("agent_rag", _agent_rag_node)
builder.add_node("agent_redator", _agent_redator_node)
builder.add_node("agent_exercicios", _agent_exercicios_node)

builder.set_entry_point("router")
builder.add_edge("router", "agent_dados")
builder.add_edge("agent_dados", "agent_rag")
builder.add_edge("agent_rag", "agent_redator")
builder.add_conditional_edges("agent_redator", _should_run_exercicios)
builder.add_edge("agent_exercicios", END)

graph = builder.compile()
