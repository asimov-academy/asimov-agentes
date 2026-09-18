import { render, screen } from "@testing-library/react";
import { describe, expect, it } from "vitest";
import { Dica } from "./Dica";

const AVISO = "A Meta cobra por mensagem, com 1.000 grátis por número por mês.";

describe("Dica", () => {
  it("o aviso ocupa só um ícone, e o texto fica escondido até o hover ou o foco", () => {
    render(<Dica texto={AVISO} />);
    const gatilho = screen.getByRole("note", { name: AVISO });

    const balao = gatilho.parentElement?.querySelector("span[aria-hidden]");
    expect(balao?.textContent).toBe(AVISO);
    // Parado ele é invisível; quem o abre são as duas regras nomeadas do Tailwind.
    expect(balao?.className).toContain("opacity-0");
    expect(balao?.className).toContain("group-hover/dica:opacity-100");
    expect(gatilho.parentElement?.className).toContain("group/dica");
  });

  it("abre pelo teclado também, não só pelo mouse", () => {
    render(<Dica texto={AVISO} />);
    const gatilho = screen.getByRole("note", { name: AVISO });
    const balao = gatilho.parentElement?.querySelector("span[aria-hidden]");

    expect(gatilho.tabIndex).toBe(0);
    expect(balao?.className).toContain("group-focus-within/dica:opacity-100");
  });
});
