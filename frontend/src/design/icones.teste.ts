import { readdirSync, readFileSync, statSync } from "node:fs";
import { join } from "node:path";
import { describe, expect, it } from "vitest";
import { ICONES } from "./icones";

function arquivos(pasta: string): string[] {
  return readdirSync(pasta).flatMap((nome: string) => {
    const caminho = join(pasta, nome);
    if (statSync(caminho).isDirectory()) return arquivos(caminho);
    return /\.tsx$/.test(nome) ? [caminho] : [];
  });
}

describe("sistema de ícones", () => {
  it("traz os cinquenta do sprite do design system", () => {
    expect(Object.keys(ICONES)).toHaveLength(50);
    for (const grupo of ["nav-", "act-", "stat-", "comm-", "cont-", "sys-"]) {
      expect(Object.keys(ICONES).some((n) => n.startsWith(grupo))).toBe(true);
    }
  });

  it("tela nenhuma desenha SVG à mão: ícone sai do sprite", () => {
    const culpados = arquivos("src/telas").filter((caminho) =>
      readFileSync(caminho, "utf8").includes("<svg"),
    );
    expect(culpados).toEqual([]);
  });
});
