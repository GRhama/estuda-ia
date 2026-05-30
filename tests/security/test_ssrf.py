"""Testes de segurança SSRF — 100% coverage obrigatório."""
import pytest
import httpx
import respx
from core.sanitizer import check_ssrf, ALLOWED_HOSTS
from core.data_fetcher import safe_fetch


class TestSSRFGuard:
    def test_metadata_aws_bloqueado(self):
        with pytest.raises(ValueError, match="SSRF"):
            check_ssrf("http://169.254.169.254/latest/meta-data/")

    def test_metadata_gcp_bloqueado(self):
        with pytest.raises(ValueError, match="SSRF"):
            check_ssrf("http://metadata.google.internal/computeMetadata/v1/")

    def test_file_scheme_bloqueado(self):
        with pytest.raises(ValueError):
            check_ssrf("file:///etc/passwd")

    def test_todos_hosts_autorizados_passam(self):
        for host in ALLOWED_HOSTS:
            check_ssrf(f"https://{host}/test")

    def test_subdominio_nao_autorizado_bloqueado(self):
        with pytest.raises(ValueError, match="SSRF"):
            check_ssrf("https://evil.servicodados.ibge.gov.br/inject")

    def test_url_com_credenciais_host_invalido(self):
        with pytest.raises(ValueError, match="SSRF"):
            check_ssrf("https://user:pass@evil.com/path")


@pytest.mark.asyncio
class TestSafeFetchSSRF:
    async def test_safe_fetch_bloqueia_host_nao_autorizado(self):
        async with httpx.AsyncClient() as client:
            with pytest.raises(ValueError, match="SSRF"):
                await safe_fetch(client, "https://attacker.com/payload")

    async def test_safe_fetch_bloqueia_localhost(self):
        async with httpx.AsyncClient() as client:
            with pytest.raises(ValueError, match="SSRF"):
                await safe_fetch(client, "http://127.0.0.1:8080/admin")

    @respx.mock
    async def test_safe_fetch_host_autorizado_ok(self):
        respx.get("https://servicodados.ibge.gov.br/api/test").mock(
            return_value=httpx.Response(200, json={"ok": True})
        )
        async with httpx.AsyncClient() as client:
            resp = await safe_fetch(client, "https://servicodados.ibge.gov.br/api/test")
        assert resp.status_code == 200

    @respx.mock
    async def test_safe_fetch_nao_segue_redirect(self):
        respx.get("https://servicodados.ibge.gov.br/api/redir").mock(
            return_value=httpx.Response(301, headers={"Location": "https://evil.com"})
        )
        async with httpx.AsyncClient() as client:
            resp = await safe_fetch(client, "https://servicodados.ibge.gov.br/api/redir")
        assert resp.status_code == 301
