"""Testes de guardrails de negócio — 100% coverage obrigatório."""
import pytest
from pydantic import ValidationError

from agents.schemas.dpo import BlocoArgumentativo, TEXTO_SEM_FONTE
from agents.schemas.shared import FonteOficial
from agents.schemas.analise_texto import AnaliseTextoModoB
from agents.schemas.redacao_enem import PropostaIntervencaoENEM
from agents.schemas.redacao_unicamp import PropostaUNICAMP
from agents.schemas.exercicio import ExercicioMultiplaEscolha, AlternativasQuestao, ResolucaoQuestao
from agents.schemas.ficha_estudo import FichaEstudo


def _alt():
    return AlternativasQuestao(a="A", b="B", c="C", d="D", e="E")


# ─── REGRA 1 ────────────────────────────────────────────────────────────────

class TestRegra1DadoSemFonte:
    """Afirmação sem fonte → 'Informação não localizada em fonte oficial'."""

    def test_dado_sem_fonte_substituido(self):
        b = BlocoArgumentativo(
            argumento="A desigualdade cresceu",
            dado_estatistico="número inventado",
            localizado_em_fonte_oficial=False,
        )
        assert b.dado_estatistico == TEXTO_SEM_FONTE

    def test_texto_padrao_exato(self):
        b = BlocoArgumentativo(argumento="arg", dado_estatistico="x", localizado_em_fonte_oficial=False)
        assert b.dado_estatistico == "Informação não localizada em fonte oficial"

    def test_dado_com_fonte_nao_substituido(self):
        fonte = FonteOficial(fonte="IBGE", url="https://ibge.gov.br/dado")
        b = BlocoArgumentativo(
            argumento="A pobreza aumentou",
            dado_estatistico="48 milhões de pessoas",
            fonte=fonte,
            localizado_em_fonte_oficial=True,
        )
        assert b.dado_estatistico == "48 milhões de pessoas"

    def test_sem_dado_localizado_false_ok(self):
        b = BlocoArgumentativo(argumento="argumento puro", localizado_em_fonte_oficial=False)
        assert b.dado_estatistico is None


# ─── REGRA 2 ────────────────────────────────────────────────────────────────

class TestRegra2RssSemAviso:
    """Dado de RSS → aviso_rss obrigatório. Sem aviso → ValidationError."""

    def test_rss_sem_aviso_levanta_validation_error(self):
        with pytest.raises(ValidationError) as exc_info:
            FonteOficial(
                fonte="Gov.br RSS",
                url="https://www.gov.br/rss.xml",
                is_rss=True,
            )
        assert "aviso_rss" in str(exc_info.value)

    def test_rss_com_aviso_ok(self):
        f = FonteOficial(
            fonte="Senado RSS",
            url="https://senado.leg.br/feed",
            is_rss=True,
            aviso_rss="Conteúdo RSS — verificar data e autoria antes de citar.",
        )
        assert f.is_rss and f.aviso_rss

    def test_api_sem_rss_sem_aviso_ok(self):
        f = FonteOficial(fonte="IBGE API", url="https://servicodados.ibge.gov.br/api/v1/localidades")
        assert not f.is_rss
        assert f.aviso_rss is None


# ─── REGRA 3 ────────────────────────────────────────────────────────────────

class TestRegra3AnaliseModoB:
    """Modo B (título/autor sem trecho) → campo limitacao obrigatório."""

    def test_sem_limitacao_levanta_erro(self):
        with pytest.raises(ValidationError) as exc_info:
            AnaliseTextoModoB(
                titulo_obra="Dom Casmurro",
                autor="Machado de Assis",
                recursos_estilisticos=[],
                temas=["ciúme"],
                limitacao="",
            )
        assert "limitacao" in str(exc_info.value)

    def test_limitacao_apenas_espacos_levanta_erro(self):
        with pytest.raises(ValidationError):
            AnaliseTextoModoB(
                titulo_obra="Dom Casmurro",
                autor="Machado de Assis",
                recursos_estilisticos=[],
                temas=[],
                limitacao="   ",
            )

    def test_com_limitacao_ok(self):
        a = AnaliseTextoModoB(
            titulo_obra="O Cortiço",
            autor="Aluísio Azevedo",
            recursos_estilisticos=[],
            temas=["naturalismo"],
            limitacao="Baseado em fontes secundárias — texto original não fornecido.",
        )
        assert a.modo == "titulo_autor"


# ─── REGRA 4 ────────────────────────────────────────────────────────────────

class TestRegra4ENEMProposta:
    """Proposta ENEM sem qualquer dos 4 campos → não entrega."""

    @pytest.mark.parametrize("campo", ["agente", "acao", "meio", "finalidade"])
    def test_campo_vazio_bloqueia(self, campo):
        dados = {"agente": "gov", "acao": "implementar", "meio": "via lei", "finalidade": "reduzir"}
        dados[campo] = ""
        with pytest.raises(ValidationError) as exc_info:
            PropostaIntervencaoENEM(**dados)
        assert campo in str(exc_info.value)

    @pytest.mark.parametrize("campo", ["agente", "acao", "meio", "finalidade"])
    def test_campo_ausente_bloqueia(self, campo):
        dados = {"agente": "gov", "acao": "implementar", "meio": "via lei", "finalidade": "reduzir"}
        del dados[campo]
        with pytest.raises(ValidationError):
            PropostaIntervencaoENEM(**dados)

    def test_proposta_completa_passa(self):
        p = PropostaIntervencaoENEM(
            agente="O Ministério da Educação",
            acao="deve ampliar o PROUNI",
            meio="por meio de editais anuais",
            finalidade="a fim de democratizar o acesso ao ensino superior",
        )
        assert all([p.agente, p.acao, p.meio, p.finalidade])


# ─── REGRA 5 ────────────────────────────────────────────────────────────────

class TestRegra5UNICAMPAdequacao:
    """UNICAMP carta sem vocalivo ou despedida → adequacao_genero=False."""

    def test_vocalivo_e_despedida_preserva_true(self):
        p = PropostaUNICAMP(
            genero_textual="carta aberta",
            tem_vocalivo=True, tem_despedida=True, adequacao_genero=True,
        )
        assert p.adequacao_genero is True

    def test_sem_vocalivo_forca_false(self):
        p = PropostaUNICAMP(
            genero_textual="carta",
            tem_vocalivo=False, tem_despedida=True, adequacao_genero=True,
        )
        assert p.adequacao_genero is False

    def test_sem_despedida_forca_false(self):
        p = PropostaUNICAMP(
            genero_textual="carta",
            tem_vocalivo=True, tem_despedida=False, adequacao_genero=True,
        )
        assert p.adequacao_genero is False

    def test_sem_ambos_forca_false(self):
        p = PropostaUNICAMP(
            genero_textual="carta",
            tem_vocalivo=False, tem_despedida=False, adequacao_genero=True,
        )
        assert p.adequacao_genero is False


# ─── REGRA 7 ────────────────────────────────────────────────────────────────

class TestRegra7Exercicios:
    """Exercícios: passo_a_passo/por_que_incorretas/distribuição 5/7/3."""

    def test_exatas_sem_passo_a_passo_invalido(self):
        res = ResolucaoQuestao(resposta_correta="a", explicacao="ok", passo_a_passo=[], por_que_incorretas={})
        with pytest.raises(ValidationError) as exc_info:
            ExercicioMultiplaEscolha(
                enunciado="2+2?", alternativas=_alt(),
                resolucao=res, area="exatas", conceito="adição",
            )
        assert "passo_a_passo" in str(exc_info.value)

    def test_humanas_sem_por_que_incorretas_invalido(self):
        res = ResolucaoQuestao(resposta_correta="b", explicacao="ok", passo_a_passo=[], por_que_incorretas={})
        with pytest.raises(ValidationError) as exc_info:
            ExercicioMultiplaEscolha(
                enunciado="quem foi?", alternativas=_alt(),
                resolucao=res, area="humanas", conceito="napoleão",
            )
        assert "por_que_incorretas" in str(exc_info.value)

    def test_distribuicao_correta_aceita(self):
        exercicios = []
        for i in range(5):
            res = ResolucaoQuestao(resposta_correta="a", explicacao="ok", passo_a_passo=["p"], por_que_incorretas={})
            exercicios.append(ExercicioMultiplaEscolha(
                enunciado="q", alternativas=_alt(), resolucao=res, area="exatas", conceito=f"e{i}"
            ))
        for i in range(7):
            res = ResolucaoQuestao(resposta_correta="b", explicacao="ok", passo_a_passo=[], por_que_incorretas={"a": "e"})
            exercicios.append(ExercicioMultiplaEscolha(
                enunciado="q", alternativas=_alt(), resolucao=res, area="humanas", conceito=f"h{i}"
            ))
        for i in range(3):
            res = ResolucaoQuestao(resposta_correta="c", explicacao="ok", passo_a_passo=[], por_que_incorretas={})
            exercicios.append(ExercicioMultiplaEscolha(
                enunciado="q", alternativas=_alt(), resolucao=res, area="linguagens", conceito=f"l{i}"
            ))
        f = FichaEstudo(resumo="ok", pontos_chave=[], exercicios=exercicios)
        assert len(f.exercicios) == 15

    def test_distribuicao_incorreta_levanta_erro(self):
        exercicios = []
        for i in range(15):
            res = ResolucaoQuestao(resposta_correta="a", explicacao="ok", passo_a_passo=["p"], por_que_incorretas={})
            exercicios.append(ExercicioMultiplaEscolha(
                enunciado="q", alternativas=_alt(), resolucao=res, area="exatas", conceito=f"c{i}"
            ))
        with pytest.raises(ValidationError):
            FichaEstudo(resumo="ok", pontos_chave=[], exercicios=exercicios)
