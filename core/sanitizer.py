import re
import ipaddress
from urllib.parse import urlparse
from loguru import logger

WORD_BLOCK_LIST = [
    # Automutilação e suicídio
    "como se machucar", "como se matar", "suicídio passo a passo",
    "método de suicídio", "como tomar remédio para morrer",
    "cortar o pulso", "overdose intencional",
    # Violência física
    "como matar alguém", "como espancar", "como torturar",
    "assassinato perfeito", "como desaparecer com corpo",
    "mutilação", "arma caseira", "como fazer faca",
    # Armas e explosivos
    "como fazer bomba", "explosivo caseiro", "como fabricar arma",
    "pólvora caseira", "como modificar arma", "silenciador caseiro",
    "molotov", "coquetel explosivo",
    # Drogas — produção e uso
    "como fazer droga", "síntese de drogas", "como produzir crack",
    "como refinar cocaína", "laboratório de drogas",
    "como usar seringa", "como cheirar", "como fumar pedra",
    # Conteúdo sexual e grooming
    "conteúdo sexual", "pornografia", "sexo explícito",
    "como seduzir menor", "como conquistar criança",
    "nudes de menor", "foto íntima de adolescente",
    "como convencer a tirar foto",
    # Assédio e stalking
    "como rastrear pessoa", "como descobrir endereço de alguém",
    "como invadir celular", "como espionar namorada",
    "como seguir pessoa sem ser visto", "como encontrar menor sozinho",
    # Crimes financeiros
    "como clonar cartão", "como fazer golpe", "phishing tutorial",
    "como roubar dados", "como invadir conta bancária",
    "estelionato passo a passo",
    # Radicalização e ódio
    "como recrutar para seita", "manifesto de ódio",
    "como incitar violência", "discurso de ódio",
    "como se radicalizar", "terrorismo doméstico",
    # Evasão do sistema
    "como fugir dos pais", "como sair de casa sem ser visto",
    "como mentir para responsável", "como esconder de professor",
    "como desativar controle parental",
    # Manipulação psicológica de menor
    "como manipular adolescente", "como ganhar confiança de criança",
    "como isolar namorada", "como controlar pessoa",
    "gaslighting tutorial", "como fazer alguém depender de mim",
]

ALLOWED_HOSTS = frozenset({
    "servicodados.ibge.gov.br",
    "ipeadata.gov.br",
    "api.worldbank.org",
    "terrabrasilis.dpi.inpe.br",
    "paho.org",
    "lexml.gov.br",
    "senado.leg.br",
    "www.gov.br",
    "restcountries.com",
    "whc.unesco.org",
    "query.wikidata.org",
    "fenix.fao.org",
    "documents.un.org",
    "pt.wikipedia.org",
    "en.wikipedia.org",
    "api.openalex.org",
    "scielo.br",
    "eutils.ncbi.nlm.nih.gov",
    "www.gutenberg.org",
    "gutendex.com",
    "www.dominiopublico.gov.br",
    "agenciabrasil.ebc.com.br",
})

_PRIVATE_RANGES = [
    ipaddress.ip_network("127.0.0.0/8"),
    ipaddress.ip_network("10.0.0.0/8"),
    ipaddress.ip_network("172.16.0.0/12"),
    ipaddress.ip_network("192.168.0.0/16"),
    ipaddress.ip_network("169.254.0.0/16"),
    ipaddress.ip_network("0.0.0.0/8"),
]

_INJECTION_RE = re.compile(
    r"<(?:system|instruction|prompt|role|assistant|human|ai)\b",
    re.IGNORECASE,
)

MAX_INPUT_LEN = 2_000
MAX_OUTPUT_LEN = 50_000


def normalizar(texto: str) -> str:
    texto = texto.lower()
    texto = re.sub(r"[0@]", "o", texto)
    texto = re.sub(r"[1!]", "i", texto)
    texto = re.sub(r"3", "e", texto)
    texto = re.sub(r"[\-\.\s]+", " ", texto)
    return texto


def word_block_check(user_input: str) -> bool:
    """Nível 1: match direto. Nível 2: após normalização l33t."""
    lower = user_input.lower()
    if any(termo in lower for termo in WORD_BLOCK_LIST):
        return True
    normalized = normalizar(user_input)
    return any(termo in normalized for termo in WORD_BLOCK_LIST)


def sanitize_user_input(raw: str) -> str:
    """Valida e sanitiza input do usuário. Levanta ValueError se inválido ou bloqueado."""
    if not raw or not raw.strip():
        raise ValueError("input vazio")
    if len(raw) > MAX_INPUT_LEN:
        raise ValueError(f"input excede {MAX_INPUT_LEN} caracteres")
    if word_block_check(raw):
        logger.bind(security=True).warning("word_block_triggered", input_len=len(raw))
        raise ValueError("BLOCKED")
    return raw.strip()


def sanitize_api_output(raw: str) -> str:
    """Sanitiza output de API externa antes de usar em prompt (indirect injection)."""
    if not raw:
        return ""
    raw = re.sub(r"[\x00-\x08\x0b\x0c\x0e-\x1f\x7f]", "", raw)
    raw = _INJECTION_RE.sub("[REDACTED]", raw)
    if len(raw) > MAX_OUTPUT_LEN:
        raw = raw[:MAX_OUTPUT_LEN]
    return raw.strip()


def check_ssrf(url: str) -> None:
    """Levanta ValueError se URL aponta para IP privado ou host não autorizado."""
    parsed = urlparse(url)
    host = parsed.hostname
    if not host:
        raise ValueError(f"URL inválida: {url!r}")
    try:
        addr = ipaddress.ip_address(host)
        if any(addr in net for net in _PRIVATE_RANGES):
            logger.bind(security=True).warning("ssrf_private_ip", host=host)
            raise ValueError(f"SSRF bloqueado: IP privado '{host}'")
    except ValueError as exc:
        if "SSRF" in str(exc):
            raise
        # hostname — cai na allowlist
    if host not in ALLOWED_HOSTS:
        logger.bind(security=True).warning("ssrf_unknown_host", host=host)
        raise ValueError(f"SSRF bloqueado: host não autorizado '{host}'")
