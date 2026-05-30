import pytest
from pydantic import ValidationError
from agents.schemas.redacao_enem import CompetenciasENEM, PropostaIntervencaoENEM, RedacaoENEM


class TestCompetenciasENEM:
    def test_total_correto(self):
        c = CompetenciasENEM(
            c1_norma_culta=160, c2_compreensao=160,
            c3_argumentacao=160, c4_coesao=160, c5_proposta=160,
            total=800,
        )
        assert c.total == 800

    def test_total_incorreto_levanta_erro(self):
        with pytest.raises(ValidationError) as exc_info:
            CompetenciasENEM(
                c1_norma_culta=160, c2_compreensao=160,
                c3_argumentacao=160, c4_coesao=160, c5_proposta=160,
                total=900,
            )
        assert "total" in str(exc_info.value)

    def test_competencia_acima_200_invalida(self):
        with pytest.raises(ValidationError):
            CompetenciasENEM(
                c1_norma_culta=201, c2_compreensao=160,
                c3_argumentacao=160, c4_coesao=160, c5_proposta=160,
                total=841,
            )

    def test_zero_valido(self):
        c = CompetenciasENEM(
            c1_norma_culta=0, c2_compreensao=0,
            c3_argumentacao=0, c4_coesao=0, c5_proposta=0,
            total=0,
        )
        assert c.total == 0


class TestPropostaIntervencaoENEM:
    def test_proposta_completa_ok(self):
        p = PropostaIntervencaoENEM(
            agente="O governo federal",
            acao="deve implementar políticas públicas",
            meio="por meio de campanhas de conscientização",
            finalidade="a fim de reduzir a desigualdade social",
        )
        assert p.agente and p.acao and p.meio and p.finalidade

    @pytest.mark.parametrize("campo", ["agente", "acao", "meio", "finalidade"])
    def test_campo_vazio_levanta_erro(self, campo):
        dados = {"agente": "gov", "acao": "impl", "meio": "via lei", "finalidade": "reduzir"}
        dados[campo] = ""
        with pytest.raises(ValidationError) as exc_info:
            PropostaIntervencaoENEM(**dados)
        assert campo in str(exc_info.value)

    @pytest.mark.parametrize("campo", ["agente", "acao", "meio", "finalidade"])
    def test_campo_ausente_levanta_erro(self, campo):
        dados = {"agente": "gov", "acao": "impl", "meio": "via lei", "finalidade": "reduzir"}
        del dados[campo]
        with pytest.raises(ValidationError):
            PropostaIntervencaoENEM(**dados)


class TestRedacaoENEM:
    def test_redacao_completa_ok(self):
        proposta = PropostaIntervencaoENEM(
            agente="O Estado", acao="deve agir",
            meio="por políticas", finalidade="para reduzir disparidade",
        )
        r = RedacaoENEM(
            introducao="Introdução...",
            desenvolvimento=["Primeiro argumento...", "Segundo argumento..."],
            conclusao="Conclusão...",
            proposta_intervencao=proposta,
        )
        assert r.fontes == []
        assert r.competencias is None
