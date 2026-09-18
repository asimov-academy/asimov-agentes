import { render, screen, waitFor, fireEvent } from "@testing-library/react";
import { beforeEach, describe, expect, it, vi } from "vitest";
import { api, type EstadoDoCopiloto, type SessaoDoCopiloto } from "../api/cliente";
import { Copiloto } from "./Copiloto";

const VAZIA: SessaoDoCopiloto = { id: "s1", estado: "parado", erro: "", mensagens: [], propostas: [] };

const VINCULO = {
  vinculada: true,
  cli: "claude_code",
  nome: "Claude Code",
  assinatura: "Claude Pro ou Max",
  conta: "operador@exemplo.com.br",
  comando: "asimov ia",
};

function estado(partes: Partial<EstadoDoCopiloto> = {}): EstadoDoCopiloto {
  return { vinculo: VINCULO, sessao: VAZIA, ...partes };
}

describe("Copiloto", () => {
  beforeEach(() => vi.restoreAllMocks());

  it("sem conta vinculada, ensina o comando do terminal em vez de abrir um chat morto", async () => {
    vi.spyOn(api, "copiloto").mockResolvedValue(
      estado({ vinculo: { ...VINCULO, vinculada: false } }),
    );
    render(<Copiloto aoFechar={() => {}} />);
    await waitFor(() => expect(screen.getByText("asimov ia")).toBeDefined());
    expect(screen.queryByLabelText(/o que você quer/i)).toBeNull();
  });

  it("com conta vinculada, o pedido vai para a API e a tela passa a esperar", async () => {
    vi.spyOn(api, "copiloto").mockResolvedValue(estado());
    const falou = vi.spyOn(api, "copilotoFala").mockResolvedValue({
      ...VAZIA,
      estado: "pensando",
      mensagens: [{ autor: "operador", texto: "crie um agente", em: "2026-09-18T12:00:00Z" }],
    });
    render(<Copiloto aoFechar={() => {}} />);

    const campo = await screen.findByLabelText(/o que você quer/i);
    fireEvent.change(campo, { target: { value: "crie um agente" } });
    fireEvent.click(screen.getByRole("button", { name: /enviar/i }));

    await waitFor(() => expect(falou).toHaveBeenCalledWith("crie um agente"));
    await waitFor(() => expect(screen.getByText(/pensando e lendo/i)).toBeDefined());
  });

  it("proposta só muda alguma coisa depois do clique em confirmar", async () => {
    const proposta = {
      id: "p1",
      tipo: "mudanca",
      titulo: "Ajustar Bella",
      resumo: "tom mais objetivo",
      situacao: "aguardando" as const,
      campos: { nome: "Bella" },
    };
    vi.spyOn(api, "copiloto").mockResolvedValue(estado({ sessao: { ...VAZIA, propostas: [proposta] } }));
    const decidiu = vi.spyOn(api, "copilotoDecide").mockResolvedValue({
      ...VAZIA,
      propostas: [{ ...proposta, situacao: "aplicada" }],
    });

    render(<Copiloto aoFechar={() => {}} />);
    await screen.findByText("Ajustar Bella");
    expect(decidiu).not.toHaveBeenCalled();

    fireEvent.click(screen.getByRole("button", { name: /confirmar/i }));
    await waitFor(() => expect(decidiu).toHaveBeenCalledWith("p1", true));
    // Resolvida, ela sai da lista do que espera decisão.
    await waitFor(() => expect(screen.queryByText("Ajustar Bella")).toBeNull());
  });

  it("agora não recusa a proposta em vez de aplicar", async () => {
    const proposta = {
      id: "p2",
      tipo: "mudanca",
      titulo: "Ajustar Bella",
      resumo: "tom mais objetivo",
      situacao: "aguardando" as const,
    };
    vi.spyOn(api, "copiloto").mockResolvedValue(estado({ sessao: { ...VAZIA, propostas: [proposta] } }));
    const decidiu = vi.spyOn(api, "copilotoDecide").mockResolvedValue({
      ...VAZIA,
      propostas: [{ ...proposta, situacao: "recusada" }],
    });

    render(<Copiloto aoFechar={() => {}} />);
    await screen.findByText("Ajustar Bella");
    fireEvent.click(screen.getByRole("button", { name: /agora não/i }));
    await waitFor(() => expect(decidiu).toHaveBeenCalledWith("p2", false));
  });
});
