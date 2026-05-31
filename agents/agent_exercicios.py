import os
import anthropic
import instructor
from loguru import logger
from graph import GraphState
from agents.schemas.exercicio import ExercicioMultiplaEscolha

_TOKEN_PER_EXERCICIO = 800
_MAX_TENTATIVAS = 3
_AREAS: list[tuple[str, int]] = [("exatas", 5), ("humanas", 7), ("linguagens", 3)]


def _build_prompt(
    tema: str,
    area: str,
    chunks: list[dict],
    conceitos_usados: list[str],
) -> str:
    fontes_str = "\n".join(
        f"- {c.get('fonte', '?')}: {c.get('texto', '')[:400]}" for c in chunks
    ) or "(nenhuma fonte disponível)"

    conceitos_str = (
        f"Conceitos já usados (NÃO repetir): {', '.join(conceitos_usados)}"
        if conceitos_usados
        else ""
    )

    area_instrucoes = {
        "exatas": "Inclua obrigatoriamente resolução passo_a_passo (lista de passos).",
        "humanas": "Inclua obrigatoriamente por_que_incorretas (dict letra→explicação para cada alternativa errada).",
        "linguagens": "Foco em língua portuguesa, literatura ou interpretação de texto.",
    }

    return (
        "Gere UMA questão de múltipla escolha (5 alternativas a-e) sobre o tema abaixo.\n"
        f"Área: {area}. {area_instrucoes.get(area, '')}\n"
        f"{conceitos_str}\n\n"
        f"Fontes de referência:\n{fontes_str}\n\n"
        f"Tema: <tema>{tema}</tema>"
    )


def _make_instructor_client() -> instructor.Instructor:
    anth = anthropic.Anthropic(api_key=os.environ.get("ANTHROPIC_API_KEY", ""))
    return instructor.from_anthropic(anth)


def _gerar_exercicio_com_retry(
    client: instructor.Instructor,
    model: str,
    tema: str,
    area: str,
    chunks: list[dict],
    conceitos_usados: list[str],
    rid: str,
    max_tentativas: int = _MAX_TENTATIVAS,
) -> ExercicioMultiplaEscolha:
    prompt = _build_prompt(tema, area, chunks, conceitos_usados)
    last_exc: Exception | None = None

    for attempt in range(max_tentativas):
        try:
            result = client.chat.completions.create(
                model=model,
                max_tokens=_TOKEN_PER_EXERCICIO,
                messages=[{"role": "user", "content": prompt}],
                response_model=ExercicioMultiplaEscolha,
            )
            if result.conceito not in conceitos_usados:
                return result
            logger.warning(
                f"[{rid}] conceito duplicado '{result.conceito}' tentativa {attempt + 1}/{max_tentativas}"
            )
            last_exc = RuntimeError(f"conceito duplicado: {result.conceito}")
        except Exception as e:
            logger.warning(
                f"[{rid}] exercicio area={area} falhou tentativa {attempt + 1}/{max_tentativas}: {type(e).__name__}"
            )
            last_exc = e
            if attempt == max_tentativas - 1:
                raise

    raise RuntimeError(
        f"[{rid}] exercicio area={area}: falhou após {max_tentativas} tentativas"
    ) from last_exc


async def run(state: GraphState) -> GraphState:
    rid = state["request_id"]
    tema = state["input"]
    chunks = state["chunks_rag"]
    model = os.environ.get("MODEL", "claude-sonnet-4-20250514")

    logger.debug(f"[{rid}] agent_exercicios: gerando 15 questões (5 exatas / 7 humanas / 3 linguagens)")

    client = _make_instructor_client()
    exercicios: list[ExercicioMultiplaEscolha] = []

    for area, count in _AREAS:
        for _ in range(count):
            conceitos_usados = [e.conceito for e in exercicios]
            ex = _gerar_exercicio_com_retry(client, model, tema, area, chunks, conceitos_usados, rid)
            exercicios.append(ex)

    logger.debug(f"[{rid}] agent_exercicios: 15 questões OK")
    output = {**state["output"], "exercicios": [e.model_dump() for e in exercicios]}
    return {**state, "output": output}
