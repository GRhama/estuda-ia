from typing import Optional, List
from pydantic import BaseModel, model_validator
from agents.schemas.shared import FonteOficial


class PropostaUNICAMP(BaseModel):
    genero_textual: str
    tem_vocalivo: bool
    tem_despedida: bool
    adequacao_genero: bool

    @model_validator(mode="after")
    def inferir_adequacao(self) -> "PropostaUNICAMP":
        if not self.tem_vocalivo or not self.tem_despedida:
            object.__setattr__(self, "adequacao_genero", False)
        return self


class RedacaoUNICAMP(BaseModel):
    titulo: Optional[str] = None
    proposta: PropostaUNICAMP
    texto: str
    fontes: List[FonteOficial] = []
