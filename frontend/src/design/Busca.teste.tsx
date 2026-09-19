import { fireEvent, render, screen } from "@testing-library/react";
import { describe, expect, it, vi } from "vitest";
import { Busca } from "./Busca";

const EMPRESAS = [
  { id: "1", nome: "Loja Exemplo" },
  { id: "2", nome: "Clínica Exemplo" },
];

describe("Busca do cabeçalho", () => {
  it("fechada é só a lupa, e o campo não pega tabulação", () => {
    render(<Busca valor="" aoMudar={() => {}} rotulo="Buscar agente" placeholder="nome" />);
    const lupa = screen.getByRole("button", { name: "Buscar agente" });
    expect(lupa.getAttribute("aria-expanded")).toBe("false");
    expect(screen.getByLabelText("Buscar agente", { selector: "input" }).tabIndex).toBe(-1);
  });

  it("clicar abre o campo, e o que se digita sai para a tela", () => {
    const mudou = vi.fn();
    render(<Busca valor="" aoMudar={mudou} rotulo="Buscar agente" placeholder="nome" />);
    fireEvent.click(screen.getByRole("button", { name: "Buscar agente" }));
    const campo = screen.getByLabelText("Buscar agente", { selector: "input" });
    expect(campo.tabIndex).toBe(0);
    fireEvent.change(campo, { target: { value: "ana" } });
    expect(mudou).toHaveBeenCalledWith("ana");
  });

  it("Esc limpa e fecha", () => {
    const mudou = vi.fn();
    render(<Busca valor="ana" aoMudar={mudou} rotulo="Buscar agente" placeholder="nome" />);
    fireEvent.click(screen.getByRole("button", { name: "Buscar agente" }));
    fireEvent.keyDown(screen.getByLabelText("Buscar agente", { selector: "input" }), {
      key: "Escape",
    });
    expect(mudou).toHaveBeenCalledWith("");
  });

  it("com opções, ela escolhe: o texto filtra a lista e o clique aplica", () => {
    const escolheu = vi.fn();
    render(
      <Busca
        valor="clí"
        aoMudar={() => {}}
        rotulo="Escolher empresa"
        placeholder="nome da empresa"
        opcoes={EMPRESAS}
        escolhida=""
        aoEscolher={escolheu}
      />,
    );
    fireEvent.click(screen.getByRole("button", { name: "Escolher empresa" }));
    expect(screen.queryByRole("button", { name: "Loja Exemplo" })).toBeNull();
    fireEvent.click(screen.getByRole("button", { name: "Clínica Exemplo" }));
    expect(escolheu).toHaveBeenCalledWith("2");
  });

  it("fechada com empresa escolhida, o nome dela fica à vista", () => {
    render(
      <Busca
        valor=""
        aoMudar={() => {}}
        rotulo="Escolher empresa"
        placeholder="nome da empresa"
        opcoes={EMPRESAS}
        escolhida="1"
        aoEscolher={() => {}}
      />,
    );
    expect(screen.getByRole("button", { name: "Escolher empresa" }).textContent).toContain(
      "Loja Exemplo",
    );
  });
});
