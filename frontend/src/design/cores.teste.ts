import { readdirSync, readFileSync, statSync } from "node:fs";
import { join } from "node:path";
import { describe, expect, it } from "vitest";

/** Cor mora no `tailwind.config.ts` e em lugar nenhum mais.
 *  Regra de spec/frontend.md, seção 3: tela e componente usam o nome do token. */
function arquivos(pasta: string): string[] {
  return readdirSync(pasta).flatMap((nome: string) => {
    const caminho = join(pasta, nome);
    if (statSync(caminho).isDirectory()) return arquivos(caminho);
    return /\.(ts|tsx|css)$/.test(nome) ? [caminho] : [];
  });
}

describe("tokens de cor", () => {
  it("ninguém escreve hexadecimal fora da configuração do Tailwind", () => {
    const culpados = arquivos("src").filter((caminho) =>
      /#[0-9a-fA-F]{3,8}\b|\brgba?\(/.test(readFileSync(caminho, "utf8")),
    );
    expect(culpados).toEqual([]);
  });
});
