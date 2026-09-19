import { readFileSync } from "node:fs";
import { describe, expect, it } from "vitest";

/** O rodapé do popup diz o que foi salvo com o nome de cada campo em português.
 *
 *  Faltando um, o operador lia o nome cru da coluna: "salvei restringe_temas, memoria_ativa".
 *  O `Record<keyof EdicaoDoAgente, string>` já segura isso no TypeScript; este teste segura o
 *  contrário, o nome que sobra depois de o campo sair da edição.
 */
function campos(fonte: string, inicio: string): string[] {
  const corpo = fonte.slice(fonte.indexOf(inicio) + inicio.length);
  return [...corpo.slice(0, corpo.indexOf("};")).matchAll(/^ {2}(\w+)[?]?:/gm)].map((m) => m[1]);
}

describe("o que o salvar diz", () => {
  it("cada campo editável tem nome em português, e nenhum nome sobra", () => {
    const daApi = campos(
      readFileSync("src/api/cliente.ts", "utf8"),
      "export type EdicaoDoAgente = {",
    );
    const daTela = campos(
      readFileSync("src/telas/agente/Ficha.tsx", "utf8"),
      "const NOME_DO_CAMPO: Record<keyof EdicaoDoAgente, string> = {",
    );
    expect(daApi.length).toBeGreaterThan(10);
    expect([...daTela].sort()).toEqual([...daApi].sort());
  });
});
