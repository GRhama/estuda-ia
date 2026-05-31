from typing import Dict, List, Literal
from pydantic import BaseModel, Field, model_validator


class AlternativasQuestao(BaseModel):
    a: str
    b: str
    c: str
    d: str
    e: str


class ResolucaoQuestao(BaseModel):
    resposta_correta: Literal["a", "b", "c", "d", "e"]
    explicacao: str
    passo_a_passo: List[str] = Field(
        default_factory=list,
        description="Obrigatório para questões de exatas: liste cada passo da resolução.",
    )
    por_que_incorretas: Dict[str, str] = Field(
        default_factory=dict,
        description="Obrigatório para questões de humanas: explique por que cada alternativa errada está incorreta.",
    )


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
