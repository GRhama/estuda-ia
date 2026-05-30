from typing import List
from pydantic import BaseModel, model_validator
from agents.schemas.shared import FonteOficial
from agents.schemas.exercicio import ExercicioMultiplaEscolha


class FichaEstudo(BaseModel):
    resumo: str
    pontos_chave: List[str]
    exercicios: List[ExercicioMultiplaEscolha]
    fontes: List[FonteOficial] = []

    @model_validator(mode="after")
    def validate_distribuicao_exercicios(self) -> "FichaEstudo":
        total = len(self.exercicios)
        if total != 15:
            return self
        exatas = sum(1 for e in self.exercicios if e.area == "exatas")
        humanas = sum(1 for e in self.exercicios if e.area == "humanas")
        linguagens = sum(1 for e in self.exercicios if e.area == "linguagens")
        if exatas != 5 or humanas != 7 or linguagens != 3:
            raise ValueError(
                f"Distribuição incorreta: {exatas}/exatas {humanas}/humanas "
                f"{linguagens}/linguagens. Esperado: 5/7/3"
            )
        return self
