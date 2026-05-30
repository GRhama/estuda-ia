from typing import List
from loguru import logger

TIPO_VALIDOS = {"resumo", "redacao", "dpo", "analise_texto", "ficha_estudo"}

DISCIPLINAS_FONTES: dict[str, list[str]] = {
    "historia": [
        "ibge", "ipea", "worldbank", "lexml", "senado", "gov_br",
        "wikidata", "wikipedia_pt", "wikipedia_en", "openalex", "scielo",
    ],
    "geografia": [
        "ibge", "inpe", "worldbank", "restcountries", "fao",
        "wikidata", "wikipedia_pt", "wikipedia_en", "openalex",
    ],
    "biologia": [
        "pubmed", "scielo", "openalex", "paho",
        "wikidata", "wikipedia_pt", "wikipedia_en",
    ],
    "quimica": [
        "pubmed", "scielo", "openalex",
        "wikidata", "wikipedia_pt", "wikipedia_en",
    ],
    "fisica": [
        "pubmed", "scielo", "openalex",
        "wikidata", "wikipedia_pt", "wikipedia_en",
    ],
    "matematica": [
        "wikidata", "wikipedia_pt", "wikipedia_en", "openalex",
    ],
    "portugues": [
        "gutenberg", "gutendex", "dominio_publico",
        "scielo", "openalex", "wikidata", "wikipedia_pt",
    ],
    "literatura": [
        "gutenberg", "gutendex", "dominio_publico",
        "scielo", "openalex", "wikidata", "wikipedia_pt", "wikipedia_en",
    ],
    "filosofia": [
        "gutenberg", "gutendex", "dominio_publico",
        "scielo", "openalex", "wikidata", "wikipedia_pt", "wikipedia_en",
    ],
    "sociologia": [
        "ibge", "ipea", "scielo", "openalex",
        "wikidata", "wikipedia_pt", "wikipedia_en", "senado", "gov_br",
    ],
    "atualidades": [
        "ibge", "ipea", "worldbank", "inpe", "paho",
        "senado", "gov_br", "fao", "onu", "wikidata", "wikipedia_pt",
    ],
}


def route(request_id: str, disciplina: str, tipo: str) -> List[str]:
    """Determina fontes autorizadas para disciplina × tipo. Sem LLM — determinístico."""
    disciplina = disciplina.lower().strip()
    tipo = tipo.lower().strip()

    if tipo not in TIPO_VALIDOS:
        raise ValueError(f"[{request_id}] tipo inválido: '{tipo}'")

    if disciplina not in DISCIPLINAS_FONTES:
        raise ValueError(f"[{request_id}] disciplina não suportada: '{disciplina}'")

    fontes = DISCIPLINAS_FONTES[disciplina]
    logger.debug(f"[{request_id}] router: {disciplina}×{tipo} → {len(fontes)} fontes")
    return fontes
