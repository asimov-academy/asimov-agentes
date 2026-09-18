import { readFileSync } from "node:fs";
import { describe, expect, it } from "vitest";

/** O design system é a única fonte de interface (spec/frontend.md, seção 3.1).
 *
 *  Peça que ele não traz pronta é montada com as primitivas dele, nunca instalada de fora. Este
 *  teste é o que segura a regra na hora do `npm install` distraído: biblioteca de componente, de
 *  ícone, de gráfico ou de animação não entra.
 */
const PERMITIDAS = ["@fontsource/inter", "@fontsource/jetbrains-mono", "react", "react-dom", "react-router-dom"];

describe("dependências do painel", () => {
  it("só entram as que a spec permite, e nenhuma biblioteca de interface", () => {
    const pacote = JSON.parse(readFileSync("package.json", "utf8"));
    expect(Object.keys(pacote.dependencies).sort()).toEqual([...PERMITIDAS].sort());
  });

  it("nem escondida entre as de desenvolvimento", () => {
    const pacote = JSON.parse(readFileSync("package.json", "utf8"));
    const proibidas = /^(@radix-ui|@headlessui|shadcn|lucide|@heroicons|react-icons|chart\.js|recharts|d3|framer-motion|@mui|antd|bootstrap)/;
    const culpadas = Object.keys(pacote.devDependencies).filter((nome) => proibidas.test(nome));
    expect(culpadas).toEqual([]);
  });
});
