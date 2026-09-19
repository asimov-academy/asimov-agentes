"""Mede RAM, CPU e disco da plataforma com 1 agente nativo falando com um provedor de IA falso.

Roda no host, ao lado do Docker, com a stack já no ar (ver `.github/workflows/medicao.yml`):
  1. cria empresa, agente nativo e a conta do painel (a conversa de teste do painel é o único
     caminho por onde o canal nativo recebe imagem e áudio);
  2. amostra `docker stats` de poucos em poucos segundos, marcando a fase de cada amostra;
  3. passa por três fases: ocioso, carga de 1 agente (1 conversa nova por minuto, 3 a 5 mensagens,
     imagem e áudio no meio) e pico (N conversas ao mesmo tempo);
  4. escreve `relatorio.md` e `amostras.jsonl` em `SAIDA`.

Só biblioteca padrão. Tempos por variável de ambiente, para ensaio curto: OCIOSO_S, CARGA_S, PICO.
"""

import json
import os
import random
import re
import struct
import subprocess
import threading
import time
import urllib.error
import urllib.parse
import urllib.request
import uuid
import wave
import zlib
from io import BytesIO
from pathlib import Path
from statistics import mean

API = os.environ.get("API", "http://127.0.0.1:8000")
WAHA = os.environ.get("WAHA", "http://127.0.0.1:3000")
CHAVE = os.environ["CHAVE_API_ADMIN"]
CHAVE_WAHA = os.environ.get("WAHA_API_KEY", "")
OCIOSO_S = int(os.environ.get("OCIOSO_S", "300"))
CARGA_S = int(os.environ.get("CARGA_S", "1800"))
PICO = int(os.environ.get("PICO", "10"))
INTERVALO_S = float(os.environ.get("INTERVALO_S", "5"))
SAIDA = Path(os.environ.get("SAIDA", "medicao/saida"))
PROJETO = os.environ.get("PROJETO", "asimov")
SENHA = "Medicao-" + uuid.uuid4().hex

FRASES = [
    "Oi, tudo bem? Vocês abrem no sábado?",
    "Queria saber o preço do plano mensal e se tem desconto no anual.",
    "Entendi. E como funciona o cancelamento?",
    "Vocês aceitam pix ou só cartão?",
    "Perfeito, obrigado pela ajuda!",
]

fase_atual = "preparo"
amostras: list[dict] = []
conversas: list[dict] = []
trava = threading.Lock()


# HTTP


def chama(metodo: str, url: str, corpo: bytes | None = None, cabecalhos: dict | None = None) -> tuple[int, dict, bytes]:
    pedido = urllib.request.Request(url, data=corpo, method=metodo, headers=cabecalhos or {})
    abridor = urllib.request.build_opener(_SemRedirect)
    try:
        with abridor.open(pedido, timeout=60) as resposta:
            return resposta.status, dict(resposta.headers), resposta.read()
    except urllib.error.HTTPError as erro:
        return erro.code, dict(erro.headers), erro.read()


class _SemRedirect(urllib.request.HTTPRedirectHandler):
    # O cookie da sessão vem na própria resposta 303 do primeiro acesso.
    def redirect_request(self, *_: object) -> None:
        return None


def admin(metodo: str, caminho: str, corpo: dict | None = None) -> dict:
    status, _, bruto = chama(
        metodo,
        API + caminho,
        json.dumps(corpo).encode() if corpo is not None else None,
        {"X-Admin-Key": CHAVE, "Content-Type": "application/json"},
    )
    if status >= 300:
        raise RuntimeError(f"{metodo} {caminho}: {status} {bruto[:300]!r}")
    return json.loads(bruto or b"{}")


def multipart(campos: dict[str, str], nome: str, conteudo: bytes, tipo: str) -> tuple[bytes, str]:
    limite = uuid.uuid4().hex
    partes = []
    for chave, valor in campos.items():
        partes.append(f'--{limite}\r\nContent-Disposition: form-data; name="{chave}"\r\n\r\n{valor}\r\n'.encode())
    partes.append(
        f'--{limite}\r\nContent-Disposition: form-data; name="arquivo"; filename="{nome}"\r\n'
        f"Content-Type: {tipo}\r\n\r\n".encode()
        + conteudo
        + b"\r\n"
    )
    partes.append(f"--{limite}--\r\n".encode())
    return b"".join(partes), f"multipart/form-data; boundary={limite}"


# Arquivos de mentira, do tamanho do que chega num WhatsApp


def imagem_png(lado: int = 280) -> bytes:
    """Ruído não comprime: uns 230 KB, a ordem de grandeza de uma foto de celular reenviada."""
    linhas = b"".join(b"\x00" + random.randbytes(lado * 3) for _ in range(lado))

    def bloco(tipo: bytes, dados: bytes) -> bytes:
        return struct.pack(">I", len(dados)) + tipo + dados + struct.pack(">I", zlib.crc32(tipo + dados))

    return (
        b"\x89PNG\r\n\x1a\n"
        + bloco(b"IHDR", struct.pack(">IIBBBBB", lado, lado, 8, 2, 0, 0, 0))
        + bloco(b"IDAT", zlib.compress(linhas, 1))
        + bloco(b"IEND", b"")
    )


def audio_wav(segundos: int = 5) -> bytes:
    saida = BytesIO()
    with wave.open(saida, "wb") as arquivo:
        arquivo.setnchannels(1)
        arquivo.setsampwidth(2)
        arquivo.setframerate(16000)
        arquivo.writeframes(random.randbytes(16000 * 2 * segundos))
    return saida.getvalue()


# Preparo


class Painel:
    def __init__(self) -> None:
        codigo = admin("POST", "/admin/painel/codigo")["codigo"]
        formulario = urllib.parse.urlencode({"codigo": codigo, "senha": SENHA, "senha2": SENHA}).encode()
        status, cabecalhos, corpo = chama(
            "POST",
            API + "/painel/primeiro-acesso",
            formulario,
            {"Content-Type": "application/x-www-form-urlencoded"},
        )
        cookie = cabecalhos.get("Set-Cookie") or cabecalhos.get("set-cookie") or ""
        if status != 303 or not cookie:
            raise RuntimeError(f"primeiro acesso do painel falhou: {status} {corpo[:300]!r}")
        self.cookie = cookie.split(";", 1)[0]
        _, _, eu = chama("GET", API + "/painel/api/eu", None, {"Cookie": self.cookie})
        self.csrf = json.loads(eu)["csrf"]

    def cabecalhos(self) -> dict:
        return {"Cookie": self.cookie, "X-Painel-CSRF": self.csrf}

    def envia_arquivo(self, agente: str, conversa: str, texto: str, nome: str, conteudo: bytes, tipo: str) -> None:
        corpo, tipo_do_corpo = multipart({"texto": texto, "conversa": conversa}, nome, conteudo, tipo)
        status, _, bruto = chama(
            "POST",
            f"{API}/painel/api/agentes/{agente}/teste/arquivo",
            corpo,
            {**self.cabecalhos(), "Content-Type": tipo_do_corpo},
        )
        if status >= 300:
            raise RuntimeError(f"arquivo recusado: {status} {bruto[:300]!r}")



def prepara() -> tuple[str, str, Painel]:
    for _ in range(60):
        try:
            if chama("GET", API + "/health")[0] == 200:
                break
        except OSError:
            pass
        time.sleep(2)
    else:
        raise RuntimeError("a API não respondeu em 120 s")
    cliente = admin("POST", "/admin/clientes", {"nome": f"Empresa da Medição {uuid.uuid4().hex[:6]}"})["id"]
    agente = admin(
        "POST",
        f"/admin/clientes/{cliente}/agentes",
        {
            "nome": "Medidor",
            "canal": "nativo",
            "ferramentas": [],
            "modelos": {
                "modelo_conversa": "openai:gpt-falso",
                "modelo_auxiliar": "openai:gpt-falso",
                "modelo_visao": "openai:gpt-falso",
                "modelo_transcricao": "openai:whisper-1",
            },
        },
    )["id"]
    return cliente, agente, Painel()


def liga_sessao_waha() -> str:
    """Sem número pareado não há tráfego, mas a sessão iniciada já põe a engine GOWS de pé
    esperando o QR code, que é mais do que o contêiner recém-subido."""
    try:
        status, _, corpo = chama(
            "POST",
            WAHA + "/api/sessions",
            json.dumps({"name": "default", "start": True}).encode(),
            {"X-Api-Key": CHAVE_WAHA, "Content-Type": "application/json"},
        )
        return f"sessão da WAHA iniciada sem pareamento (HTTP {status})" if status < 300 else f"WAHA recusou a sessão: {status} {corpo[:200]!r}"
    except OSError as erro:
        return f"WAHA fora de alcance: {erro}"


# Amostragem


def _mib(texto: str) -> float:
    numero, unidade = re.match(r"([\d.]+)\s*([A-Za-z]+)", texto).groups()
    return float(numero) * {"B": 1 / 1048576, "KiB": 1 / 1024, "MiB": 1, "GiB": 1024, "kB": 1 / 1048.576, "MB": 1 / 1.048576, "GB": 953.674}[unidade]


def amostra_para_sempre() -> None:
    while fase_atual != "fim":
        inicio = time.time()
        saida = _docker("stats", "--no-stream", "--format", "{{json .}}")
        agora = {"quando": inicio, "fase": fase_atual, "conteineres": {}}
        for linha in saida.splitlines():
            dado = json.loads(linha)
            nome = dado["Name"]
            if not nome.startswith(PROJETO + "-"):
                continue
            servico = nome[len(PROJETO) + 1 :].rsplit("-", 1)[0]
            agora["conteineres"][servico] = {
                "ram_mib": _mib(dado["MemUsage"].split("/")[0]),
                "cpu": float(dado["CPUPerc"].rstrip("%") or 0),
            }
        with trava:
            amostras.append(agora)
        time.sleep(max(0.0, INTERVALO_S - (time.time() - inicio)))


# Conversas


def conversa(cliente: str, agente: str, painel: Painel, numero: int, com_midia: str | None) -> None:
    # Quem dá o nome à conversa é a API: a primeira mensagem vai sem ele e a resposta o devolve.
    nome = ""
    registro = {"fase": fase_atual, "conversa": numero, "enviadas": 0, "respondidas": 0, "esperas": []}
    caminho = f"/admin/clientes/{cliente}/agentes/{agente}/terminal"
    vistas = 0
    quantas = random.randint(3, 5)
    for indice in range(quantas):
        texto = FRASES[indice % len(FRASES)]
        inicio = time.time()
        try:
            if com_midia == "imagem" and indice == 1:
                painel.envia_arquivo(agente, nome, "olha essa foto", "foto.png", imagem_png(), "image/png")
            elif com_midia == "audio" and indice == 1:
                painel.envia_arquivo(agente, nome, "", "audio.wav", audio_wav(), "audio/wav")
            else:
                nome = admin("POST", caminho, {"texto": texto, **({"conversa": nome} if nome else {})})["conversa"]
            registro["enviadas"] += 1
            # O turno inclui buffer, provedor e o tempo de "digitando": espera a resposta chegar
            # inteira antes da próxima fala, como um contato de verdade.
            while time.time() - inicio < 180:
                time.sleep(2)
                leitura = admin("GET", f"{caminho}/{nome}?depois={vistas}")
                if leitura["mensagens"] and not leitura["respondendo"] and not leitura["digitando"]:
                    vistas = leitura["proxima"]
                    registro["respondidas"] += 1
                    registro["esperas"].append(round(time.time() - inicio, 1))
                    break
        except Exception as erro:  # noqa: BLE001  (a medição segue; a falha aparece no relatório)
            registro.setdefault("erros", []).append(str(erro)[:200])
        time.sleep(random.uniform(3, 8))
    with trava:
        conversas.append(registro)


def midia_da_vez(numero: int) -> str | None:
    return {0: "imagem", 1: "audio"}.get(numero % 3)


# Disco


def _docker(*argumentos: str) -> str:
    try:
        return subprocess.run(["docker", *argumentos], capture_output=True, text=True, check=False).stdout.strip()
    except FileNotFoundError:  # ensaio do roteiro numa máquina sem Docker
        return ""


def disco() -> dict:
    usuario = os.environ.get("POSTGRES_USER", "asimov")
    banco = os.environ.get("POSTGRES_DB", "asimov")
    postgres = _docker("exec", f"{PROJETO}-postgres-1", "psql", "-U", usuario, "-d", banco, "-tAc", f"select pg_database_size('{banco}')")
    def du(conteiner: str, pasta: str) -> int:
        return int((_docker("exec", f"{PROJETO}-{conteiner}-1", "du", "-sk", pasta).split() or ["0"])[0]) * 1024
    return {
        "postgres": int(postgres or 0),
        "midia": du("api", "/var/lib/asimov/midia"),
        "redis": du("redis", "/data"),
    }


# Relatório

CENARIOS = {
    "essencial": ["postgres", "redis", "api", "worker", "caddy"],
    "essencial + WAHA": ["postgres", "redis", "api", "worker", "caddy", "waha"],
    "essencial + copiloto": ["postgres", "redis", "api", "worker", "caddy", "copiloto"],
    "tudo": ["postgres", "redis", "api", "worker", "caddy", "waha", "copiloto"],
}
FASES = ["ocioso", "carga", "pico"]


def relatorio(antes: dict, depois_carga: dict, observacoes: list[str]) -> str:
    linhas = ["# Medição de recursos: 1 agente nativo, provedor de IA falso", ""]
    nucleos = os.cpu_count()
    meminfo = Path("/proc/meminfo")
    memoria = int(re.search(r"MemTotal:\s+(\d+)", meminfo.read_text()).group(1)) // 1024 if meminfo.exists() else 0
    linhas += [f"Runner: `{os.uname().machine}`, {nucleos} vCPU, {memoria} MB de RAM. CPU em % de 1 vCPU (100% = um núcleo cheio).", ""]
    linhas += [f"- {o}" for o in observacoes] + [""]

    servicos = sorted({s for a in amostras for s in a["conteineres"]} - {"mock"})
    linhas += ["## Por contêiner", "", "| Contêiner | Fase | RAM média (MiB) | RAM pico (MiB) | CPU média (%) | CPU pico (%) |", "|---|---|---|---|---|---|"]
    for servico in servicos:
        for fase in FASES:
            pontos = [a["conteineres"][servico] for a in amostras if a["fase"] == fase and servico in a["conteineres"]]
            if pontos:
                ram, cpu = [p["ram_mib"] for p in pontos], [p["cpu"] for p in pontos]
                linhas.append(f"| {servico} | {fase} | {mean(ram):.0f} | {max(ram):.0f} | {mean(cpu):.1f} | {max(cpu):.1f} |")

    linhas += ["", "## Soma por cenário", "", "A soma é feita amostra a amostra, então o pico é o da soma e não a soma dos picos.", "", "| Cenário | Fase | RAM média (MiB) | RAM pico (MiB) | CPU média (%) | CPU pico (%) |", "|---|---|---|---|---|---|"]
    for cenario, membros in CENARIOS.items():
        for fase in FASES:
            somas = [
                (sum(a["conteineres"].get(m, {}).get("ram_mib", 0) for m in membros), sum(a["conteineres"].get(m, {}).get("cpu", 0) for m in membros))
                for a in amostras
                if a["fase"] == fase
            ]
            if somas:
                ram, cpu = [s[0] for s in somas], [s[1] for s in somas]
                linhas.append(f"| {cenario} | {fase} | {mean(ram):.0f} | {max(ram):.0f} | {mean(cpu):.1f} | {max(cpu):.1f} |")

    linhas += ["", "## Conversas", "", "| Fase | Conversas | Mensagens enviadas | Respondidas | Espera média (s) | Espera máxima (s) | Erros |", "|---|---|---|---|---|---|---|"]
    for fase in ("carga", "pico"):
        dela = [c for c in conversas if c["fase"] == fase]
        esperas = [e for c in dela for e in c["esperas"]] or [0]
        linhas.append(
            f"| {fase} | {len(dela)} | {sum(c['enviadas'] for c in dela)} | {sum(c['respondidas'] for c in dela)} "
            f"| {mean(esperas):.1f} | {max(esperas):.1f} | {sum(len(c.get('erros', [])) for c in dela)} |"
        )

    feitas = max(1, len([c for c in conversas if c["fase"] == "carga"]))
    linhas += ["", "## Disco", "", f"Crescimento na fase de carga ({feitas} conversas, 1 em cada 3 com imagem de ~230 KB e 1 em cada 3 com áudio de ~160 KB):", "", "| O quê | Antes | Depois | Cresceu | Por conversa | 30 dias a 100 conversas/dia | 30 dias a 1 conversa/min |", "|---|---|---|---|---|---|---|"]
    for chave, rotulo in (("postgres", "Banco (Postgres)"), ("midia", "Volume de mídia"), ("redis", "Redis (AOF)")):
        cresceu = depois_carga[chave] - antes[chave]
        por = cresceu / feitas
        linhas.append(
            f"| {rotulo} | {antes[chave] / 1048576:.1f} MB | {depois_carga[chave] / 1048576:.1f} MB | {cresceu / 1048576:.2f} MB "
            f"| {por / 1024:.0f} KB | {por * 3000 / 1048576:.0f} MB | {por * 43200 / 1073741824:.1f} GB |"
        )
    linhas += ["", "### `docker system df`", "", "```", _docker("system", "df"), "```", "", "### Imagens", "", "```", _docker("images", "--format", "table {{.Repository}}:{{.Tag}}\t{{.Size}}"), "```"]
    return "\n".join(linhas) + "\n"


def principal() -> None:
    global fase_atual
    SAIDA.mkdir(parents=True, exist_ok=True)
    cliente, agente, painel = prepara()
    observacoes = [liga_sessao_waha()]
    threading.Thread(target=amostra_para_sempre, daemon=True).start()

    fase_atual = "ocioso"
    print(f"ocioso por {OCIOSO_S} s", flush=True)
    time.sleep(OCIOSO_S)

    antes = disco()
    fase_atual = "carga"
    print(f"carga por {CARGA_S} s: 1 conversa nova por minuto", flush=True)
    fios = []
    for numero in range(max(1, CARGA_S // 60)):
        fio = threading.Thread(target=conversa, args=(cliente, agente, painel, numero, midia_da_vez(numero)))
        fio.start()
        fios.append(fio)
        time.sleep(60)
    for fio in fios:
        fio.join()
    depois_carga = disco()

    fase_atual = "pico"
    print(f"pico: {PICO} conversas ao mesmo tempo", flush=True)
    fios = [threading.Thread(target=conversa, args=(cliente, agente, painel, n, midia_da_vez(n))) for n in range(PICO)]
    for fio in fios:
        fio.start()
    for fio in fios:
        fio.join()
    fase_atual = "fim"

    texto = relatorio(antes, depois_carga, observacoes)
    (SAIDA / "relatorio.md").write_text(texto, encoding="utf-8")
    with (SAIDA / "amostras.jsonl").open("w", encoding="utf-8") as arquivo:
        for amostra in amostras:
            arquivo.write(json.dumps(amostra) + "\n")
    (SAIDA / "conversas.json").write_text(json.dumps(conversas, indent=1), encoding="utf-8")
    print(texto)

    enviadas = sum(c["enviadas"] for c in conversas)
    respondidas = sum(c["respondidas"] for c in conversas)
    if not enviadas or respondidas < 0.9 * enviadas:
        raise SystemExit(f"só {respondidas} de {enviadas} mensagens tiveram resposta: a carga não foi a pedida")


if __name__ == "__main__":
    principal()
