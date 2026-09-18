import { readFileSync } from "node:fs";
import { describe, expect, it } from "vitest";

/** Texto legível sobre os fundos escuros, na régua da WCAG AA (4,5:1).
 *
 *  `dim` e `muted` nasceram em cinzas escuros que davam 1,9:1 e 2,4:1 sobre o preto: rótulo de
 *  campo, placeholder e texto de apoio sumiam na tela. Este teste guarda o piso; quem quiser um tom
 *  mais apagado precisa mexer aqui e explicar. As cores vêm do `tailwind.config.ts`, nunca daqui.
 */
function luminancia(cor: string): number {
  const canal = (c: number) => {
    const v = c / 255;
    return v <= 0.04045 ? v / 12.92 : ((v + 0.055) / 1.055) ** 2.4;
  };
  const n = parseInt(cor.slice(1), 16);
  return 0.2126 * canal((n >> 16) & 255) + 0.7152 * canal((n >> 8) & 255) + 0.0722 * canal(n & 255);
}

function contraste(a: string, b: string): number {
  const [x, y] = [luminancia(a), luminancia(b)];
  return (Math.max(x, y) + 0.05) / (Math.min(x, y) + 0.05);
}

const config = readFileSync("tailwind.config.ts", "utf8");

function token(nome: string): string {
  const achado = config.match(new RegExp(`\\b${nome}:\\s*"([^"]+)"`));
  if (!achado) throw new Error(`token ${nome} não está no tailwind.config.ts`);
  return achado[1];
}

const FUNDOS = ["void", "surface", "panel"] as const;
/** Todo token que vira cor de texto na tela. */
const TEXTOS = ["texto", "muted", "dim", "ciano", "ok", "atencao", "perigo"] as const;

describe("contraste de texto", () => {
  it.each(TEXTOS)("%s passa nos 4,5:1 da WCAG AA sobre os três fundos", (nome) => {
    for (const fundo of FUNDOS) {
      expect(contraste(token(nome), token(fundo))).toBeGreaterThanOrEqual(4.5);
    }
  });

  it("a hierarquia é texto, depois muted, depois dim", () => {
    const sobre = (nome: string) => contraste(token(nome), token("void"));
    expect(sobre("texto")).toBeGreaterThan(sobre("muted"));
    expect(sobre("muted")).toBeGreaterThan(sobre("dim"));
  });

  it("o CSS do login usa os mesmos tons do Tailwind", () => {
    const css = readFileSync("../backend/app/painel/estaticos/painel.css", "utf8");
    for (const nome of [...TEXTOS, ...FUNDOS]) {
      expect(css).toContain(`--${nome}: ${token(nome)};`);
    }
  });
});
