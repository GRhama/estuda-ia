from typing import Optional, List
from pydantic import BaseModel, model_validator
from agents.schemas.shared import FonteOficial

TEXTO_SEM_FONTE = "Informação não localizada em fonte oficial"


class BlocoArgumentativo(BaseModel):
    argumento: str
    dado_estatistico: Optional[str] = None
    fonte: Optional[FonteOficial] = None
    localizado_em_fonte_oficial: bool

    @model_validator(mode="after")
    def guardrail_dado_sem_fonte(self) -> "BlocoArgumentativo":
        if self.dado_estatistico and not self.localizado_em_fonte_oficial:
            object.__setattr__(self, "dado_estatistico", TEXTO_SEM_FONTE)
        return self


class DPO(BaseModel):
    tema: str
    tese: str
    blocos: List[BlocoArgumentativo]
    conclusao: str
    fontes: List[FonteOficial] = []
