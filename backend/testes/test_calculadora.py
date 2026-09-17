"""Calculadora (`ia/ferramentas/calculadora.py`): toda conta do agente passa por ela."""

from datetime import datetime

import pytest

from app.ia.ferramentas.calculadora import FUSO_BRASILIA, calcular


@pytest.mark.parametrize(
    ("conta", "resultado"),
    [
        ("(199,90 * 3) * 0.9", "539,73"),
        ("7 // 2", "3"),
        ("10 / 4", "2,5"),
        ("2 ** 3", "8"),
        ("-(5 - 8)", "3"),
        # Testes do operador na VPS: ponto de milhar e vírgula decimal, como o contato escreve.
        ("87.432 × 5.291", "462.602.712"),
        ("918.273 ÷ 47,6", "19.291,4495798319"),
        ("(3.847 × 219) - (15.632 / 8) + 2.901²", "9.256.340"),
        ("1.299,90 * 3", "3.899,7"),
        ("0.125 * 8", "1"),
        ("-1.500 + 200", "-1.300"),
        ("1 / 3", "0,3333333333"),
        ("10 ** 20 / 4", "25.000.000.000.000.000.000"),
    ],
)
def test_calculadora_faz_conta_exata(conta: str, resultado: str) -> None:
    assert calcular(conta) == resultado


@pytest.mark.parametrize(
    ("conta", "resultado"),
    [
        # Pedido do operador: qualquer conta de atendimento passa pela calculadora.
        ("raiz(144)", "12"),
        ("√(2,25)", "1,5"),
        ("2^10", "1.024"),
        ("arredonda(10 / 3; 2)", "3,33"),
        ("arredonda(1.299,90 * 0,85; 2)", "1.104,92"),
        ("arredonda(2,5)", "3"),
        ("porcentagem(15; 3.450)", "517,5"),
        ("3.450 * 15%", "517,5"),
        ("7 % 2", "1"),
        ("variacao_percentual(80; 100)", "25"),
        ("media(7; 8,5; 10)", "8,5"),
        ("soma(1.000; 2.500,50; 0,5)", "3.501"),
        ("max(3, 9, 4)", "9"),
        ("min(3; 9; 4)", "3"),
        ("arredonda(juros_compostos(10.000; 1; 12); 2)", "11.268,25"),
        ("arredonda(parcela(1.200; 0; 12); 2)", "100"),
        ("arredonda(parcela(10.000; 2; 12); 2)", "945,6"),
        ("fatorial(5)", "120"),
        ("log(1.000)", "3"),
        ("arredonda(ln(e); 4)", "1"),
        ("arredonda(sen(radianos(30)); 4)", "0,5"),
        ("piso(4,7) + teto(4,2)", "9"),
        ("3 x 4", "12"),
        ('dias_entre("16/09/2026"; "25/12/2026")', "100"),
        ('soma_dias("30/01/2026"; 30)', "01/03/2026"),
        ('"25/12/2026" - "16/09/2026"', "Erro: esperava um número"),
    ],
)
def test_calculadora_faz_qualquer_conta_de_atendimento(conta: str, resultado: str) -> None:
    assert calcular(conta) == resultado


def test_calculadora_sabe_a_data_de_hoje_em_brasilia() -> None:

    assert calcular("hoje()") == datetime.now(FUSO_BRASILIA).strftime("%d/%m/%Y")
    assert calcular("dias_entre(hoje(); soma_dias(hoje(); 45))") == "45"


@pytest.mark.parametrize(
    "errada",
    ['dias_entre("2026-09-16"; "25/12/2026")', "fatorial(500)", "raiz(-1)", "arredonda()", "parcela(100; 1; 0)", "(1 + 2"],
)
def test_calculadora_explica_o_erro_para_o_modelo_corrigir(errada: str) -> None:
    assert calcular(errada).startswith("Erro: ")


@pytest.mark.parametrize(
    "perigosa",
    ["__import__('os').system('ls')", "9 ** 9 ** 9", "1 / 0", "a + 1", "[1] * 9", "raiz.__class__", "(lambda: 1)()", "'a' * 3",
     "((fatorial(170)^100)^100)^100", "fatorial(170) * fatorial(170) * fatorial(170) ^ 90", 'soma_dias("01/01/2026"; 10^9)'],
)
def test_calculadora_recusa_o_que_nao_e_conta(perigosa: str) -> None:
    assert calcular(perigosa).startswith("Erro")
