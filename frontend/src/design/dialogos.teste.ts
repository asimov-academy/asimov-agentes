import { readdirSync, readFileSync, statSync } from "node:fs";
import { join } from "node:path";
import { describe, expect, it } from "vitest";

/** O painel não usa caixa nativa do navegador.
 *
 *  O X do popup do agente chamava `window.confirm` antes de fechar. Onde o navegador suprime a
 *  caixa nativa (embutido num app, modo quiosque, bloqueio de diálogo), ela devolve "não" sem
 *  aparecer, e o popup simplesmente não fechava: o botão parecia morto. Fora isso, `confirm`,
 *  `alert` e `prompt` travam a página e ignoram o design system inteiro.
 *
 *  Quem precisa confirmar usa o `Modal`; quem precisa avisar usa o `Aviso`.
 */
function arquivos(pasta: string): string[] {
  return readdirSync(pasta).flatMap((nome: string) => {
    const caminho = join(pasta, nome);
    if (statSync(caminho).isDirectory()) return arquivos(caminho);
    return /\.(ts|tsx)$/.test(nome) && !/\.teste\./.test(nome) ? [caminho] : [];
  });
}

describe("diálogo nativo", () => {
  it("ninguém chama confirm, alert ou prompt", () => {
    const culpados = arquivos("src").filter((caminho) =>
      // A espreitadela para trás evita o falso positivo do método com o mesmo nome:
      // `api.prompt(id)` busca o prompt do agente e não é caixa do navegador.
      /(?<![.\w])(?:window\.)?(?:confirm|alert|prompt)\s*\(/.test(readFileSync(caminho, "utf8")),
    );
    expect(culpados).toEqual([]);
  });
});
