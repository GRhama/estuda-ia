import os
import anthropic
import instructor
from loguru import logger
from openai import OpenAI
from graph import GraphState
from agents.schemas.analise_texto import AnaliseTextoModoA, AnaliseTextoModoB

_GEMINI_BASE_URL = "https://generativelanguage.googleapis.com/v1beta/openai/"


def _is_gemini(model: str) -> bool:
    return model.startswith("gemini")

TOKEN_BUDGET_ANALISE = 4500


def _detect_modo(trecho: str | None) -> str:
    """Modo A se trecho fornecido e não vazio. Modo B caso contrário."""
    return "A" if trecho and trecho.strip() else "B"


def _build_prompt(chunks: list[dict], tema: str, trecho: str | None, modo: str) -> str:
    fontes_str = "\n".join(
        f"- {c.get('fonte', '?')} ({c.get('url', '')}): {c.get('texto', '')[:500]}"
        for c in chunks
    ) or "(nenhuma fonte disponível)"

    trecho_section = f"\nTrecho fornecido para análise:\n{trecho}\n" if modo == "A" else ""
    modo_label = "A (trecho fornecido)" if modo == "A" else "B (título/autor apenas — sem trecho)"

    return (
        "Você é um especialista em análise literária e linguística para vestibulandos do EM.\n"
        "Use APENAS as fontes abaixo. Nunca invente recursos estilísticos sem embasamento.\n\n"
        f"Fontes:\n{fontes_str}\n"
        f"{trecho_section}"
        f"\nTema: <tema>{tema}</tema>\n"
        f"Modo: {modo_label}"
    )


def _make_instructor_client(model: str = "") -> instructor.Instructor:
    if _is_gemini(model):
        oai = OpenAI(
            api_key=os.environ.get("GEMINI_API_KEY", ""),
            base_url=_GEMINI_BASE_URL,
        )
        return instructor.from_openai(oai)
    anth = anthropic.Anthropic(api_key=os.environ.get("ANTHROPIC_API_KEY", ""))
    return instructor.from_anthropic(anth)


async def run(state: GraphState) -> GraphState:
    rid = state["request_id"]
    chunks = state["chunks_rag"]
    tema = state["input"]
    trecho = state.get("trecho")

    modo = _detect_modo(trecho)
    schema = AnaliseTextoModoA if modo == "A" else AnaliseTextoModoB
    model = os.environ.get("MODEL", "claude-sonnet-4-20250514")

    logger.debug(f"[{rid}] agent_analista: Modo {modo} schema={schema.__name__}")

    client = _make_instructor_client(model)
    prompt = _build_prompt(chunks, tema, trecho, modo)

    try:
        result = client.chat.completions.create(
            model=model,
            max_tokens=TOKEN_BUDGET_ANALISE,
            messages=[{"role": "user", "content": prompt}],
            response_model=schema,
        )
        logger.debug(f"[{rid}] agent_analista: output OK (Modo {modo})")
        return {**state, "output": result.model_dump()}
    except Exception as e:
        logger.error(f"[{rid}] agent_analista falhou: {type(e).__name__}")
        raise
