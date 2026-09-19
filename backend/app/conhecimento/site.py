"""Baixa uma página pública com IP validado e teto durante a leitura."""
import asyncio
import ipaddress
import socket

import httpx


class SiteInvalido(ValueError):
    pass


async def endereco_publico(url: httpx.URL) -> str:
    if url.scheme not in ("http", "https") or not url.host or url.userinfo:
        raise SiteInvalido("use um endereço público http ou https, sem credenciais")
    if url.port not in (None, 80, 443):
        raise SiteInvalido("use uma página pública na porta HTTP ou HTTPS padrão")
    try:
        enderecos = await asyncio.get_running_loop().getaddrinfo(
            url.host, url.port or (443 if url.scheme == "https" else 80), type=socket.SOCK_STREAM
        )
    except OSError as erro:
        raise SiteInvalido("não consegui localizar essa página") from erro
    ips = [item[4][0] for item in enderecos]
    if not ips or any(not ipaddress.ip_address(ip).is_global for ip in ips):
        raise SiteInvalido("o endereço precisa apontar só para servidores públicos")
    return ips[0]


async def baixar(url: str, limite: int) -> bytes:
    atual = httpx.URL(url)
    # Sem proxy do ambiente: o IP conferido é exatamente o destino conectado.
    async with asyncio.timeout(30), httpx.AsyncClient(timeout=30, trust_env=False) as http:
        for _ in range(6):
            ip = await endereco_publico(atual)
            async with http.stream(
                "GET", atual.copy_with(host=ip),
                headers={"Host": atual.netloc.decode(), "User-Agent": "AsimovAgentes/1.0"},
                extensions={"sni_hostname": atual.host},
            ) as resposta:
                if resposta.is_redirect:
                    destino = resposta.headers.get("location")
                    if not destino:
                        raise SiteInvalido("a página redirecionou sem informar o destino")
                    atual = atual.join(destino)
                    continue
                resposta.raise_for_status()
                conteudo = bytearray()
                async for parte in resposta.aiter_bytes():
                    if len(conteudo) + len(parte) > limite:
                        raise SiteInvalido("página maior que 20 MB; use um material menor")
                    conteudo.extend(parte)
                return bytes(conteudo)
    raise SiteInvalido("a página redirecionou vezes demais")
