import os
from typing import Type
import anthropic
import instructor
from instructor.core import InstructorRetryException
from loguru import logger
from openai import AsyncOpenAI
from pydantic import BaseModel
from graph import GraphState

_GEMINI_BASE_URL = "https://generativelanguage.googleapis.com/v1beta/openai/"


def _is_gemini(model: str) -> bool:
    return model.startswith("gemini")
from agents.schemas.redacao_enem import RedacaoENEM
from agents.schemas.redacao_fuvest import RedacaoFUVEST
from agents.schemas.redacao_unicamp import RedacaoUNICAMP
from agents.schemas.redacao_unesp import RedacaoUNESP
from agents.schemas.resumo import Resumo
from agents.schemas.analise_texto import AnaliseTextoModoA
from agents.schemas.dpo import DPO
from agents.schemas.ficha_estudo import FichaEstudo

TOKEN_BUDGET: dict[str, int] = {
    "resumo": 3000,
    "redacao": 5000,
    "dpo": 6000,
    "analise_texto": 4500,
    "ficha_estudo": 12000,
}

_SCHEMA_MAP: dict[str, dict] = {
    "redacao": {
        "ENEM": RedacaoENEM,
        "FUVEST": RedacaoFUVEST,
        "UNICAMP": RedacaoUNICAMP,
        "UNESP": RedacaoUNESP,
        None: RedacaoENEM,
    },
    "resumo": {None: Resumo},
    "dpo": {None: DPO},
    "analise_texto": {None: AnaliseTextoModoA},
    "ficha_estudo": {None: FichaEstudo},
}


def _get_schema(tipo: str, banca: str | None) -> Type[BaseModel]:
    tipo_schemas = _SCHEMA_MAP.get(tipo)
    if tipo_schemas is None:
        raise ValueError(f"tipo não suportado: '{tipo}'")
    schema = tipo_schemas.get(banca) or tipo_schemas.get(None)
    if schema is None:
        raise ValueError(f"schema não encontrado: tipo={tipo} banca={banca}")
    return schema


def _build_prompt(tipo: str, chunks: list[dict], tema: str) -> str:
    fontes_str = "\n".join(
        f"- {c.get('fonte', '?')} ({c.get('url', '')}): {c.get('texto', '')[:500]}"
        for c in chunks
    ) or "(nenhuma fonte disponível)"
    return (
        "Você é um assistente acadêmico para estudantes do EM preparando FUVEST/ENEM/UNESP/UNICAMP.\n"
        "Use APENAS os dados fornecidos abaixo. Se um dado não estiver nas fontes, "
        "sinalize localizado_em_fonte_oficial=false.\n\n"
        f"Fontes:\n{fontes_str}\n\n"
        f"Tema: <tema>{tema}</tema>\n\n"
        f"Tipo de output: {tipo}"
    )


def _make_instructor_client(model: str = "") -> instructor.AsyncInstructor:
    if _is_gemini(model):
        oai = AsyncOpenAI(
            api_key=os.environ.get("GEMINI_API_KEY", ""),
            base_url=_GEMINI_BASE_URL,
        )
        return instructor.from_openai(oai)
    anth = anthropic.AsyncAnthropic(api_key=os.environ.get("ANTHROPIC_API_KEY", ""))
    return instructor.from_anthropic(anth)


async def run(state: GraphState) -> GraphState:
    rid = state["request_id"]
    tipo = state["tipo"]
    banca = state.get("banca")
    chunks = state["chunks_rag"]
    tema = state["input"]

    schema = _get_schema(tipo, banca)
    max_tokens = TOKEN_BUDGET.get(tipo, 5000)
    model = os.environ.get("MODEL", "claude-sonnet-4-20250514")

    logger.debug(f"[{rid}] agent_redator: tipo={tipo} banca={banca} schema={schema.__name__} max_tokens={max_tokens}")

    client = _make_instructor_client(model)
    prompt = _build_prompt(tipo, chunks, tema)

    try:
        if _is_gemini(model):
            result = await client.chat.completions.create(
                model=model,
                max_tokens=max_tokens,
                messages=[{"role": "user", "content": prompt}],
                response_model=schema,
            )
        else:
            result = await client.messages.create(
                model=model,
                max_tokens=max_tokens,
                messages=[{"role": "user", "content": prompt}],
                response_model=schema,
            )
        logger.debug(f"[{rid}] agent_redator: output OK ({schema.__name__})")
        return {**state, "output": result.model_dump()}
    except InstructorRetryException as e:
        logger.error(f"[{rid}] instructor max retries exceeded: {e!r}")
        raise
    except Exception as e:
        logger.error(f"[{rid}] agent_redator falhou: {type(e).__name__}: {e!r}")
        raise
