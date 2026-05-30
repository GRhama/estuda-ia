from typing import Optional, List
from pydantic import BaseModel
from agents.schemas.shared import FonteOficial


class RedacaoFUVEST(BaseModel):
    tipo_texto: str
    titulo: Optional[str] = None
    introducao: str
    desenvolvimento: List[str]
    conclusao: str
    fontes: List[FonteOficial] = []
