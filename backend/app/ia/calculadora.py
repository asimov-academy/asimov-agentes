"""Calculadora do agente: toda conta que o modelo precisa fazer passa por aqui, nunca pela cabeça dele.

Sem `eval`: a expressão vira árvore sintática e só números, operadores, as funções de FUNCOES e datas entre
aspas são avaliados. Números no formato brasileiro (ponto de milhar, vírgula decimal), como o contato escreve;
por isso os argumentos das funções se separam com `;`, como no Excel em português.
"""

import ast
import math
import operator
import re
from collections.abc import Callable
from datetime import date, datetime, timedelta, timezone
from decimal import ROUND_HALF_UP, Decimal
from typing import Any

LIMITE_EXPOENTE = 100
LIMITE_EXPRESSAO = 500
LIMITE_ARGUMENTOS = 100
LIMITE_FATORIAL = 170
# Um contato pode pedir ((fatorial(170)^100)^100)^100: sem teto, o worker gastaria memória sem fim.
LIMITE_BITS = 14_000
"""Cerca de 4.200 dígitos, abaixo do limite do Python para virar texto (4.300)."""
# Brasília sem horário de verão desde 2019. Fixo: a imagem enxuta do Python pode não ter o banco de fusos.
FUSO_BRASILIA = timezone(timedelta(hours=-3))

_OPERACOES: dict[type, Callable[..., Any]] = {
    ast.Add: operator.add,
    ast.Sub: operator.sub,
    ast.Mult: operator.mul,
    ast.Div: operator.truediv,
    ast.FloorDiv: operator.floordiv,
    ast.Mod: operator.mod,
    ast.Pow: operator.pow,
    ast.USub: operator.neg,
    ast.UAdd: operator.pos,
}

Numero = int | float


class ErroDeConta(ValueError):
    """Mensagem em português, que volta ao modelo para ele corrigir a expressão."""


def _data(texto: Any) -> date:
    if isinstance(texto, date):
        return texto
    try:
        return datetime.strptime(str(texto).strip(), "%d/%m/%Y").date()
    except ValueError as erro:
        raise ErroDeConta(f"data {texto!r} fora do formato \"dd/mm/aaaa\"") from erro


def _numero(valor: Any) -> Numero:
    if isinstance(valor, bool) or not isinstance(valor, int | float):
        raise ErroDeConta("esperava um número")
    return valor


def _fatorial(n: Any) -> int:
    n = _numero(n)
    if n != int(n) or not 0 <= n <= LIMITE_FATORIAL:
        raise ErroDeConta(f"fatorial só de inteiro de 0 a {LIMITE_FATORIAL}")
    return math.factorial(int(n))


def _log(x: Any, base: Any = 10) -> float:
    return math.log(_numero(x), _numero(base))


def _arredonda(x: Any, casas: Any = 0) -> Numero:
    """Meio para cima, como no dinheiro: 1.104,915 vira 1.104,92 (o round do Python daria 1.104,91)."""
    casas = int(_numero(casas))
    if not 0 <= casas <= 10:
        raise ErroDeConta("arredonda aceita de 0 a 10 casas")
    # repr depois de 10 casas: 1104.9149999999999 do float volta a ser 1104.915 antes de arredondar.
    exato = Decimal(repr(round(_numero(x), 10))).quantize(Decimal(1).scaleb(-casas), rounding=ROUND_HALF_UP)
    return int(exato) if casas == 0 else float(exato)


def _porcentagem(percentual: Any, total: Any) -> float:
    return _numero(percentual) / 100 * _numero(total)


def _variacao_percentual(de: Any, para: Any) -> float:
    return (_numero(para) - _numero(de)) / _numero(de) * 100


def _juros_compostos(capital: Any, taxa_percentual: Any, periodos: Any) -> float:
    return _numero(capital) * (1 + _numero(taxa_percentual) / 100) ** _numero(periodos)


def _parcela(valor: Any, taxa_percentual: Any, parcelas: Any) -> float:
    """Tabela Price: parcela fixa de um valor financiado."""
    valor, taxa, n = _numero(valor), _numero(taxa_percentual) / 100, _numero(parcelas)
    if n <= 0:
        raise ErroDeConta("número de parcelas precisa ser maior que zero")
    if taxa == 0:
        return valor / n
    return valor * taxa / (1 - (1 + taxa) ** -n)


def _media(*valores: Any) -> float:
    if not valores:
        raise ErroDeConta("média precisa de pelo menos um número")
    return sum(_numero(v) for v in valores) / len(valores)


def _hoje() -> date:
    return datetime.now(FUSO_BRASILIA).date()


FUNCOES: dict[str, Callable[..., Any]] = {
    "raiz": lambda x: math.sqrt(_numero(x)),
    "abs": lambda x: abs(_numero(x)),
    "arredonda": _arredonda,
    "piso": lambda x: math.floor(_numero(x)),
    "teto": lambda x: math.ceil(_numero(x)),
    "min": lambda *v: min(_numero(x) for x in v),
    "max": lambda *v: max(_numero(x) for x in v),
    "soma": lambda *v: sum(_numero(x) for x in v),
    "media": _media,
    "log": _log,
    "ln": lambda x: math.log(_numero(x)),
    "exp": lambda x: math.exp(_numero(x)),
    "sen": lambda x: math.sin(_numero(x)),
    "cos": lambda x: math.cos(_numero(x)),
    "tan": lambda x: math.tan(_numero(x)),
    "radianos": lambda x: math.radians(_numero(x)),
    "fatorial": _fatorial,
    "porcentagem": _porcentagem,
    "variacao_percentual": _variacao_percentual,
    "juros_compostos": _juros_compostos,
    "parcela": _parcela,
    "hoje": _hoje,
    "dias_entre": lambda inicio, fim: (_data(fim) - _data(inicio)).days,
    "soma_dias": lambda data, dias: _data(data) + timedelta(days=int(_numero(dias))),
}
# Nomes em inglês que o modelo costuma usar por hábito.
FUNCOES |= {"sqrt": FUNCOES["raiz"], "round": FUNCOES["arredonda"], "floor": FUNCOES["piso"],
            "ceil": FUNCOES["teto"], "sum": FUNCOES["soma"], "sin": FUNCOES["sen"]}
CONSTANTES: dict[str, float] = {"pi": math.pi, "e": math.e}


def _limita(valor: Any) -> Any:
    if isinstance(valor, int) and valor.bit_length() > LIMITE_BITS:
        raise ErroDeConta("número grande demais")
    return valor


def _avalia(no: ast.AST) -> Any:
    if isinstance(no, ast.Expression):
        return _avalia(no.body)
    if isinstance(no, ast.Constant) and isinstance(no.value, int | float | str) and not isinstance(no.value, bool):
        return no.value
    if isinstance(no, ast.Name) and no.id in CONSTANTES:
        return CONSTANTES[no.id]
    if isinstance(no, ast.UnaryOp) and type(no.op) in _OPERACOES:
        return _OPERACOES[type(no.op)](_numero(_avalia(no.operand)))
    if isinstance(no, ast.BinOp) and type(no.op) in _OPERACOES:
        esquerda, direita = _avalia(no.left), _avalia(no.right)
        if isinstance(no.op, ast.Pow):
            base, expoente = _numero(esquerda), _numero(direita)
            if abs(expoente) > LIMITE_EXPOENTE or (
                isinstance(base, int) and base.bit_length() * abs(expoente) > LIMITE_BITS
            ):
                raise ErroDeConta("número grande demais")
        # Data menos data dá dias; data mais número dá data.
        if isinstance(esquerda, date) or isinstance(direita, date):
            if isinstance(no.op, ast.Sub) and isinstance(esquerda, date) and isinstance(direita, date):
                return (esquerda - direita).days
            if isinstance(no.op, ast.Add | ast.Sub) and isinstance(esquerda, date):
                dias = timedelta(days=int(_numero(direita)))
                return esquerda + dias if isinstance(no.op, ast.Add) else esquerda - dias
            raise ErroDeConta("com datas, use dias_entre e soma_dias")
        return _limita(_OPERACOES[type(no.op)](_numero(esquerda), _numero(direita)))
    if isinstance(no, ast.Call) and isinstance(no.func, ast.Name) and no.func.id in FUNCOES and not no.keywords:
        if len(no.args) > LIMITE_ARGUMENTOS:
            raise ErroDeConta("argumentos demais")
        try:
            return _limita(FUNCOES[no.func.id](*(_avalia(a) for a in no.args)))
        except TypeError as erro:
            raise ErroDeConta(f"quantidade de argumentos errada em {no.func.id}") from erro
    raise ErroDeConta(
        "use números, + - * / // % ^ ** e parênteses, as funções " + ", ".join(sorted(FUNCOES))
        + ", pi, e, e datas entre aspas \"dd/mm/aaaa\""
    )


_TEXTO_ENTRE_ASPAS = re.compile(r"(\"[^\"]*\"|'[^']*')")
_NUMERO = re.compile(r"\d[\d.,]*\d|\d")
_MILHAR_BRASILEIRO = re.compile(r"[1-9]\d{0,2}(\.\d{3})+")
_PORCENTO = re.compile(r"(\d+(?:\.\d+)?)\s*%(?!\s*[\d(])")
_VEZES = re.compile(r"(?<=[\d)])\s*[xX]\s*(?=[\d(])")
_SIMBOLOS = {"×": "*", "÷": "/", "−": "-", "²": "**2", "³": "**3", "^": "**", "√": "raiz"}


def _numero_brasileiro(achado: re.Match[str]) -> str:
    """87.432 é milhar, 47,6 é decimal e 0.9 continua decimal (o modelo às vezes escreve assim)."""
    numero = achado.group()
    if "," in numero:
        return numero.replace(".", "").replace(",", ".")
    if _MILHAR_BRASILEIRO.fullmatch(numero):
        return numero.replace(".", "")
    return numero


def _trecho_em_python(trecho: str) -> str:
    for simbolo, troca in _SIMBOLOS.items():
        trecho = trecho.replace(simbolo, troca)
    # `, ` com espaço separa argumentos (hábito do modelo); vírgula colada no número é decimal.
    trecho = re.sub(r",\s+", "; ", trecho)
    trecho = _NUMERO.sub(_numero_brasileiro, trecho)
    trecho = trecho.replace(";", ",")
    trecho = _VEZES.sub("*", trecho)
    return _PORCENTO.sub(r"(\1/100)", trecho)


def para_python(expressao: str) -> str:
    """Números no formato brasileiro viram números do Python; datas entre aspas ficam como estão."""
    partes = _TEXTO_ENTRE_ASPAS.split(expressao.strip())
    return "".join(p if i % 2 else _trecho_em_python(p) for i, p in enumerate(partes))


def formato_brasileiro(valor: Any) -> str:
    if isinstance(valor, date):
        return valor.strftime("%d/%m/%Y")
    if isinstance(valor, float):
        valor = round(valor, 10)
        if valor.is_integer():
            valor = int(valor)
    # Com casas fixas: número grande em float não vira notação científica (1e+20).
    texto = str(valor) if isinstance(valor, int) else f"{valor:.10f}".rstrip("0").rstrip(".")
    inteiro, _, decimais = texto.partition(".")
    sinal = "-" if inteiro.startswith("-") else ""
    inteiro = f"{int(inteiro.lstrip('-')):,}".replace(",", ".")
    return f"{sinal}{inteiro},{decimais}" if decimais else f"{sinal}{inteiro}"


def calcular(expressao: str) -> str:
    """Faz qualquer conta com resultado exato. Toda conta passa por aqui, inclusive as simples.

    Números no formato brasileiro, como o contato escreve: 1.299,90 é mil duzentos e noventa e nove reais e
    noventa centavos. Argumentos de função separados por ponto e vírgula. Devolve no formato brasileiro.

    Operadores: + - * / // (divisão inteira) % (resto; 15% depois de um número é porcentagem) ^ ou ** e parênteses.
    Funções: raiz(x), abs(x), arredonda(x; casas), piso(x), teto(x), min(...), max(...), soma(...), media(...),
    log(x; base), ln(x), exp(x), sen(x), cos(x), tan(x) em radianos, radianos(graus), fatorial(n),
    porcentagem(percentual; total), variacao_percentual(de; para), juros_compostos(capital; taxa_percentual; periodos),
    parcela(valor; taxa_percentual; parcelas) pela tabela Price, hoje(), dias_entre("dd/mm/aaaa"; "dd/mm/aaaa"),
    soma_dias("dd/mm/aaaa"; dias). Constantes pi e e.

    Args:
        expressao: A conta. Ex.: parcela(1.299,90; 1,99; 12) ou porcentagem(15; 3.450) ou dias_entre(hoje(); "25/12/2026")
    """
    try:
        texto = para_python(expressao)
        if len(texto) > LIMITE_EXPRESSAO:
            return "Erro: conta longa demais; divida em partes."
        return formato_brasileiro(_avalia(ast.parse(texto, mode="eval")))
    except ZeroDivisionError:
        return "Erro: divisão por zero."
    except SyntaxError:
        return "Erro: expressão mal escrita; confira parênteses, operadores e o ; entre argumentos."
    except OverflowError:
        return "Erro: número grande demais."
    except (ErroDeConta, ValueError, TypeError) as erro:
        return f"Erro: {erro}"
