import { fireEvent, render, screen } from "@testing-library/react";
import { describe, expect, it, vi } from "vitest";
import { Faixa } from "./Faixa";

const EMOJIS = [
  { valor: "nenhum", rotulo: "Nenhum" },
  { valor: "pouco", rotulo: "Pouco" },
  { valor: "medio", rotulo: "Médio" },
  { valor: "muito", rotulo: "Muito" },
];

describe("Faixa", () => {
  it("devolve o valor da posição para onde o operador arrastou", () => {
    const mudou = vi.fn();
    render(<Faixa rotulo="Emoji" opcoes={EMOJIS} valor="nenhum" aoMudar={mudou} />);
    fireEvent.change(screen.getByRole("slider", { name: "Emoji" }), { target: { value: "2" } });
    expect(mudou).toHaveBeenCalledWith("medio");
  });

  it("conta o rótulo escolhido para quem usa leitor de tela", () => {
    render(<Faixa rotulo="Emoji" opcoes={EMOJIS} valor="muito" aoMudar={() => {}} />);
    const faixa = screen.getByRole("slider", { name: "Emoji" });
    expect(faixa).toHaveProperty("value", "3");
    expect(faixa.getAttribute("aria-valuetext")).toBe("Muito");
  });

  it("valor que não está na lista fica na primeira posição, sem quebrar", () => {
    render(<Faixa rotulo="Emoji" opcoes={EMOJIS} valor="livre" aoMudar={() => {}} />);
    expect(screen.getByRole("slider", { name: "Emoji" })).toHaveProperty("value", "0");
  });
});
