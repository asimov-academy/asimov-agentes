import { fireEvent, render, screen } from "@testing-library/react";
import { describe, expect, it, vi } from "vitest";
import { Interruptor } from "./Interruptor";

describe("Interruptor", () => {
  it("avisa quem controla quando o operador clica", () => {
    const mudou = vi.fn();
    render(<Interruptor ligado={false} aoMudar={mudou} rotulo="Usar emoji nas respostas" />);
    fireEvent.click(screen.getByRole("switch", { name: "Usar emoji nas respostas" }));
    expect(mudou).toHaveBeenCalledWith(true);
  });

  it("desligado não muda nada", () => {
    const mudou = vi.fn();
    render(<Interruptor ligado desligado aoMudar={mudou} rotulo="Busca na web" />);
    fireEvent.click(screen.getByRole("switch", { name: "Busca na web" }));
    expect(mudou).not.toHaveBeenCalled();
  });

  it("conta o estado para quem usa leitor de tela", () => {
    render(<Interruptor ligado aoMudar={() => {}} rotulo="Dividir resposta" />);
    expect(screen.getByRole("switch")).toHaveProperty("ariaChecked", "true");
  });
});
