import { render, screen } from "@testing-library/react";
import { describe, expect, it } from "vitest";
import { Progresso } from "./Progresso";

describe("Progresso", () => {
  it("a barra é a fração do teto da lista, não do próprio valor", () => {
    const { container } = render(<Progresso rotulo="Ana" valor={25} de={100} />);
    expect((container.querySelector("[role=meter] > div") as HTMLElement).style.width).toBe("25%");
  });

  it("teto zero não quebra a escala", () => {
    const { container } = render(<Progresso rotulo="Ana" valor={0} de={0} />);
    expect((container.querySelector("[role=meter] > div") as HTMLElement).style.width).toBe("0%");
  });

  it("valor acima do teto para na barra cheia", () => {
    const { container } = render(<Progresso rotulo="Ana" valor={180} de={100} />);
    expect((container.querySelector("[role=meter] > div") as HTMLElement).style.width).toBe("100%");
  });

  it("conta o que mede para quem usa leitor de tela", () => {
    render(<Progresso rotulo="turnos da Ana" valor={7} de={10} escrito="7 turnos" />);
    const medidor = screen.getByRole("meter", { name: "turnos da Ana" });
    expect(medidor.getAttribute("aria-valuenow")).toBe("7");
    expect(medidor.getAttribute("aria-valuemax")).toBe("10");
    expect(screen.getByText("7 turnos")).toBeDefined();
  });
});
