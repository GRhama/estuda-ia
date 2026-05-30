from loguru import logger
from graph import GraphState


async def run(state: GraphState) -> GraphState:
    """Stub Sprint 5 — agent_exercicios não implementado ainda."""
    rid = state["request_id"]
    logger.debug(f"[{rid}] agent_exercicios: stub (Sprint 5)")
    return state
