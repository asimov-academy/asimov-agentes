import { readdirSync, readFileSync } from "node:fs";
import { join } from "node:path";
import { describe, expect, it } from "vitest";

/** Os controles do cabeçalho são sempre as mesmas peças, na mesma altura.
 *
 *  Cada tela já desenhou o próprio grupo de opções, com altura, arredondamento e peso de fonte
 *  diferentes, ao lado de uma lupa de 44px: três controles para a mesma pergunta. Agora existem
 *  `Busca`, `Segmentos` e `Botao`, e este teste recusa o grupo desenhado à mão.
 */
function telas(): { caminho: string; fonte: string }[] {
  const pasta = "src/telas";
  return readdirSync(pasta)
    .filter((nome) => nome.endsWith(".tsx") && !nome.includes(".teste."))
    .map((nome) => ({ caminho: join(pasta, nome), fonte: readFileSync(join(pasta, nome), "utf8") }));
}

/** O `acoes={...}` do `Cabecalho`, contando as chaves: dentro dos popups da mesma tela o botão
 *  pequeno continua valendo, e um recorte por linha pegaria eles também. */
function acoesDoCabecalho(fonte: string): string {
  const inicio = fonte.indexOf("acoes={");
  if (inicio < 0) return "";
  let nivel = 0;
  for (let i = inicio + "acoes=".length; i < fonte.length; i++) {
    if (fonte[i] === "{") nivel++;
    if (fonte[i] === "}" && --nivel === 0) return fonte.slice(inicio, i);
  }
  return "";
}

/** A ordem do cabeçalho no painel inteiro: buscar, filtrar, agir. */
const ORDEM = ["Busca", "Segmentos", "Botao"];

describe("controles do cabeçalho", () => {
  it("a ordem é sempre buscar, filtrar, agir", () => {
    for (const { caminho, fonte } of telas()) {
      const encontrados = [...acoesDoCabecalho(fonte).matchAll(/<(Busca|Segmentos|Botao)\b/g)].map(
        (m) => m[1],
      );
      const posicoes = encontrados.map((peca) => ORDEM.indexOf(peca));
      expect(
        posicoes.every((p, i) => i === 0 || posicoes[i - 1] <= p),
        `${caminho}: ${encontrados.join(", ")}`,
      ).toBe(true);
    }
  });

  it("ninguém desenha um grupo de opções à mão: para isso existe o Segmentos", () => {
    const culpados = telas()
      .filter(({ fonte }) => /role="group"/.test(fonte))
      .map(({ caminho }) => caminho);
    expect(culpados).toEqual([]);
  });

  it("botão do cabeçalho tem a altura dos outros controles, 44px", () => {
    const culpados = telas()
      .filter(({ fonte }) => /<Botao\b[^>]*\bpequeno\b/.test(acoesDoCabecalho(fonte)))
      .map(({ caminho }) => caminho);
    expect(culpados).toEqual([]);
  });
});
