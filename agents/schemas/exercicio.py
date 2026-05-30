from typing import Optional, Dict, List, Literal
from pydantic import BaseModel, model_validator


class AlternativasQuestao(BaseModel):
    a: str
    b: str
    c: str
    d: str
    e: str


class ResolucaoQuestao(BaseModel):
    resposta_correta: Literal["a", "b", "c", "d", "e"]
    explicacao: str
    passo_a_passo: Optional[List[str]] = None
    por_que_incorretas: Optional[Dict[str, str]] = None


class ExercicioMultiplaEscolha(BaseModel):
    enunciado: str
    alternativas: AlternativasQuestao
    resolucao: ResolucaoQuestao
    area: Literal["exatas", "humanas", "linguagens"]
    conceito: str

    @model_validator(mode="after")
    def validate_area_requirements(self) -> "ExercicioMultiplaEscolha":
        if self.area == "exatas" and not self.resolucao.passo_a_passo:
            raise ValueError("passo_a_passo obrigatório para questões de exatas")
        if self.area == "humanas" and not self.resolucao.por_que_incorretas:
            raise ValueError("por_que_incorretas obrigatório para questões de humanas")
        return self
