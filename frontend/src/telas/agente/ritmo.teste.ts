import { readFileSync } from "node:fs";
import { describe, expect, it } from "vitest";

/** Os presets de ritmo existem em dois lugares: o servidor os escreve no agente
 *  (`backend/app/conversas/divisao.py`) e a tela mostra o que eles valem antes de salvar.
 *
 *  Duplicação de número é duplicação que envelhece calada: aqui ela é conferida.
 */
function doBackend(): Record<string, number[]> {
  const fonte = readFileSync("../backend/app/conversas/divisao.py", "utf8");
  const corpo = fonte.slice(fonte.indexOf("RITMOS: dict"));
  const presets: Record<string, number[]> = {};
  for (const [, nome, bloco] of corpo.matchAll(/"(\w+)": \{([^}]+)\}/g)) {
    const numero = (campo: string) =>
      Number(new RegExp(`"${campo}": (\\d+)`).exec(bloco)?.[1] ?? NaN);
    presets[nome] = [
      numero("buffer_segundos"),
      numero("digitacao_caracteres_por_segundo"),
      numero("digitacao_maximo_segundos"),
    ];
  }
  return presets;
}

function daTela(): Record<string, number[]> {
  const fonte = readFileSync("src/telas/agente/Ficha.tsx", "utf8");
  const inicio = "const NUMEROS_DO_RITMO: Record<string, [number, number, number]> = {";
  const corpo = fonte.slice(fonte.indexOf(inicio) + inicio.length);
  const presets: Record<string, number[]> = {};
  for (const [, nome, numeros] of corpo.slice(0, corpo.indexOf("};")).matchAll(
    /(\w+): \[([\d, ]+)\]/g,
  )) {
    presets[nome] = numeros.split(",").map((n) => Number(n.trim()));
  }
  return presets;
}

describe("presets de ritmo", () => {
  it("a tela mostra os mesmos números que o servidor grava", () => {
    const servidor = doBackend();
    expect(Object.keys(servidor)).toHaveLength(3);
    expect(daTela()).toEqual(servidor);
  });
});
