from typing import Optional, List, Literal
from pydantic import BaseModel, model_validator
from agents.schemas.shared import FonteOficial


class RecursoEstilistico(BaseModel):
    recurso: str
    trecho: str
    efeito: str


class AnaliseTextoModoA(BaseModel):
    modo: Literal["trecho"] = "trecho"
    titulo_obra: Optional[str] = None
    autor: Optional[str] = None
    recursos_estilisticos: List[RecursoEstilistico]
    temas: List[str]
    contexto_historico: Optional[str] = None
    fontes: List[FonteOficial] = []


class AnaliseTextoModoB(BaseModel):
    """Modo B: título/autor fornecidos, sem trecho — limitacao obrigatório (REGRA 3)."""
    modo: Literal["titulo_autor"] = "titulo_autor"
    titulo_obra: str
    autor: str
    recursos_estilisticos: List[RecursoEstilistico]
    temas: List[str]
    contexto_historico: Optional[str] = None
    limitacao: str
    fontes: List[FonteOficial] = []

    @model_validator(mode="after")
    def validate_limitacao(self) -> "AnaliseTextoModoB":
        if not self.limitacao or not self.limitacao.strip():
            raise ValueError("campo 'limitacao' obrigatório no Modo B (análise sem trecho)")
        return self
