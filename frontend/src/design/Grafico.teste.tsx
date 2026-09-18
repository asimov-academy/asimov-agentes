import { fireEvent, render, screen } from "@testing-library/react";
import { describe, expect, it } from "vitest";
import { Grafico } from "./Grafico";

const PONTOS = [
  { rotulo: "15/09", valor: 3 },
  { rotulo: "16/09", valor: 0 },
  { rotulo: "17/09", valor: 9 },
];

describe("Grafico", () => {
  it("conta o que desenha para quem usa leitor de tela", () => {
    render(<Grafico tipo="area" pontos={PONTOS} />);
    expect(screen.getByRole("img").textContent).toBe("15/09: 3, 16/09: 0, 17/09: 9");
  });

  it("um ponto por fatia, inclusive o dia zerado", () => {
    const { container } = render(<Grafico tipo="area" pontos={PONTOS} />);
    expect(container.querySelectorAll("circle")).toHaveLength(3);
  });

  it("a primeira e a última fatia ficam escritas embaixo, sem precisar do mouse", () => {
    const { container } = render(<Grafico tipo="area" pontos={PONTOS} />);
    const eixo = container.querySelector("figure > div");
    expect(eixo?.textContent).toBe("15/0916/0917/09");
  });

  it("o valor do ponto aparece quando o mouse chega nele", () => {
    const { container } = render(
      <Grafico tipo="area" pontos={PONTOS} rotuloDoValor={(p) => `${p.valor} turnos`} />,
    );
    fireEvent.mouseEnter(container.querySelectorAll("circle")[2]);
    const aviso = container.querySelector("figcaption");
    expect(aviso?.textContent).toBe("17/09 9 turnos");
  });

  it("período sem nenhum valor não quebra a escala", () => {
    const zerado = [
      { rotulo: "15/09", valor: 0 },
      { rotulo: "16/09", valor: 0 },
    ];
    const { container } = render(<Grafico tipo="barras" pontos={zerado} />);
    const alturas = [...container.querySelectorAll("rect")].map((r) => r.getAttribute("height"));
    expect(alturas).toEqual(["0", "0"]);
  });

  it("a rosca desenha uma fatia por modelo e some quando não houve gasto", () => {
    const { container, rerender } = render(
      <Grafico tipo="rosca" pontos={[{ rotulo: "a", valor: 2 }, { rotulo: "b", valor: 1 }]} />,
    );
    expect(container.querySelectorAll("path")).toHaveLength(2);

    rerender(<Grafico tipo="rosca" pontos={[{ rotulo: "a", valor: 0 }]} />);
    expect(container.querySelectorAll("path")).toHaveLength(0);
  });
});
