import { render, screen, fireEvent, waitFor } from "@testing-library/react";
import { MemoryRouter } from "react-router-dom";
import { beforeEach, describe, expect, it, vi } from "vitest";
import { api, type Agente } from "../api/cliente";
import { Agentes } from "./Agentes";

function agente(nome: string, empresa: string): Agente {
  return {
    id: nome,
    nome,
    empresa,
    canal: "nativo",
    situacao: "treinamento",
    avatar: null,
    avatar_cor: "ciano",
    perfil: { funcao: "vendas" },
  } as unknown as Agente;
}

describe("Lista de agentes", () => {
  beforeEach(() => {
    vi.restoreAllMocks();
    vi.spyOn(api, "agentes").mockResolvedValue([
      agente("Ana", "Loja Exemplo"),
      agente("Caio", "Clínica Exemplo"),
    ]);
  });

  it("a lupa filtra por nome do agente e da empresa, sem consultar de novo", async () => {
    render(
      <MemoryRouter>
        <Agentes empresas={[]} />
      </MemoryRouter>,
    );
    expect(await screen.findByText("Ana")).toBeDefined();

    fireEvent.click(screen.getByRole("button", { name: "Buscar agente" }));
    const campo = screen.getByLabelText("Buscar agente", { selector: "input" });

    fireEvent.change(campo, { target: { value: "clínica" } });
    await waitFor(() => expect(screen.queryByText("Ana")).toBeNull());
    expect(screen.getByText("Caio")).toBeDefined();

    fireEvent.change(campo, { target: { value: "ana" } });
    await waitFor(() => expect(screen.queryByText("Caio")).toBeNull());
    expect(api.agentes).toHaveBeenCalledTimes(1);
  });

  it("cada linha diz o que o agente faz e em qual empresa", async () => {
    render(
      <MemoryRouter>
        <Agentes empresas={[]} />
      </MemoryRouter>,
    );
    expect(await screen.findByText("Vendedor em Loja Exemplo")).toBeDefined();
  });
});
