from typing import Optional, List
from pydantic import BaseModel, Field, model_validator
from agents.schemas.shared import FonteOficial


class CompetenciasENEM(BaseModel):
    c1_norma_culta: int = Field(ge=0, le=200)
    c2_compreensao: int = Field(ge=0, le=200)
    c3_argumentacao: int = Field(ge=0, le=200)
    c4_coesao: int = Field(ge=0, le=200)
    c5_proposta: int = Field(ge=0, le=200)
    total: int = Field(ge=0, le=1000)

    @model_validator(mode="after")
    def validate_total(self) -> "CompetenciasENEM":
        esperado = (
            self.c1_norma_culta + self.c2_compreensao
            + self.c3_argumentacao + self.c4_coesao + self.c5_proposta
        )
        if self.total != esperado:
            raise ValueError(f"total {self.total} != soma das competências {esperado}")
        return self


class PropostaIntervencaoENEM(BaseModel):
    agente: str
    acao: str
    meio: str
    finalidade: str

    @model_validator(mode="after")
    def validate_campos_obrigatorios(self) -> "PropostaIntervencaoENEM":
        for campo in ("agente", "acao", "meio", "finalidade"):
            val = getattr(self, campo, None)
            if not val or not val.strip():
                raise ValueError(f"'{campo}' obrigatório na proposta de intervenção ENEM")
        return self


class RedacaoENEM(BaseModel):
    introducao: str
    desenvolvimento: List[str]
    conclusao: str
    proposta_intervencao: PropostaIntervencaoENEM
    competencias: Optional[CompetenciasENEM] = None
    fontes: List[FonteOficial] = []
