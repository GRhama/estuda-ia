from typing import Optional, Literal
from pydantic import BaseModel, model_validator


class FonteOficial(BaseModel):
    fonte: str
    url: str
    trecho: Optional[str] = None
    is_rss: bool = False
    aviso_rss: Optional[str] = None

    @model_validator(mode="after")
    def rss_requires_aviso(self) -> "FonteOficial":
        if self.is_rss and not self.aviso_rss:
            raise ValueError("aviso_rss obrigatório para dados de fontes RSS")
        return self


class BancaRelevancia(BaseModel):
    banca: Literal["ENEM", "FUVEST", "UNESP", "UNICAMP"]
    relevante: bool
    justificativa: str


class FontePublica(BaseModel):
    """Response model exposto ao frontend — sem campos internos."""
    fonte: str
    url: str
    trecho: Optional[str] = None
