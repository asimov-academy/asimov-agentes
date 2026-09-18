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
  it("traz os cinquenta do sprite, mais os desenhados no mesmo padrão", () => {
    expect(Object.keys(ICONES).length).toBeGreaterThanOrEqual(50);
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

  /** A regra valia só para `telas/`, e os dois SVG à mão do painel estavam em `design/`: o certo
   *  dos passos e o giro do botão ocupado, os dois com o equivalente parado no banco. */
  it("componente nenhum desenha SVG à mão, fora dos que são desenho", () => {
    const desenham = ["Grafico.tsx", "Carregando.tsx", "Medidor.tsx", "Icone.tsx", "Marca.tsx"];
    const culpados = arquivos("src/design")
      .filter((caminho) => !desenham.some((nome) => caminho.endsWith(nome)))
      .filter((caminho) => readFileSync(caminho, "utf8").includes("<svg"));
    expect(culpados).toEqual([]);
  });
});
