from typing import List
from pydantic import BaseModel
from agents.schemas.shared import FonteOficial


class Resumo(BaseModel):
    titulo: str
    topicos: List[str]
    texto_resumido: str
    fontes: List[FonteOficial] = []
