import { fireEvent, render, screen, waitFor } from "@testing-library/react";
import { beforeEach, describe, expect, it, vi } from "vitest";
import { api, type Agente } from "../../api/cliente";
import { Ficha } from "./Ficha";

const AGENTE = {
  id: "a1",
  nome: "Bella",
  situacao: "ativo",
  canal: "nativo",
  empresa: "Loja",
  criado_em: "2026-09-01T00:00:00Z",
  emojis: "pouco",
  tom: "normal",
  ritmo: "natural",
  ferramentas: [],
  contatos_permitidos: [],
} as unknown as Agente;

describe("Ficha", () => {
  beforeEach(() => {
    vi.restoreAllMocks();
    Element.prototype.scrollIntoView = vi.fn();
    vi.spyOn(api, "agente").mockResolvedValue(AGENTE);
  });

  it("a situação não fica na ficha: ela se troca na lista", async () => {
    render(<Ficha agenteId="a1" aoFechar={() => {}} aoMudar={() => {}} />);
    await screen.findByLabelText("Nome");
    expect(screen.queryByRole("switch", { name: "Agente ativo" })).toBeNull();
  });

  it("o que ele faz fica no perfil, junto do nome", async () => {
    const perfil = vi.spyOn(api, "gravaPerfil").mockResolvedValue({
      agente: { ...AGENTE, perfil: { funcao: "vendas" } },
      prompt: "...",
    });
    render(<Ficha agenteId="a1" aoFechar={() => {}} aoMudar={() => {}} />);
    fireEvent.click(await screen.findByRole("button", { name: "Vendas" }));
    fireEvent.click(screen.getByRole("button", { name: "Salvar" }));
    await waitFor(() => expect(perfil).toHaveBeenCalledWith("a1", { funcao: "vendas" }));
  });

  it("um Salvar só, no rodapé, desligado até algo mudar", async () => {
    render(<Ficha agenteId="a1" aoFechar={() => {}} aoMudar={() => {}} />);
    const nome = await screen.findByLabelText("Nome");
    const salvar = screen.getByRole("button", { name: "Salvar" }) as HTMLButtonElement;
    expect(salvar.disabled).toBe(true);
    fireEvent.change(nome, { target: { value: "Bela" } });
    expect(salvar.disabled).toBe(false);
    expect(screen.getAllByRole("button", { name: /^Salvar/ })).toHaveLength(1);
  });

  it("trocar de aba guarda o que foi mexido, e o Salvar manda tudo", async () => {
    const edita = vi.spyOn(api, "editaAgente").mockResolvedValue({ ...AGENTE, nome: "Bela" });
    render(<Ficha agenteId="a1" aoFechar={() => {}} aoMudar={() => {}} />);
    fireEvent.change(await screen.findByLabelText("Nome"), { target: { value: "Bela" } });
    fireEvent.click(screen.getByRole("tab", { name: "Comunicação" }));
    expect(screen.getByRole("tab", { name: "Comunicação" }).getAttribute("aria-selected")).toBe(
      "true",
    );
    fireEvent.click(screen.getByRole("tab", { name: /Perfil/ }));
    expect((screen.getByLabelText("Nome") as HTMLInputElement).value).toBe("Bela");
    fireEvent.click(screen.getByRole("button", { name: "Salvar" }));
    await waitFor(() => expect(edita).toHaveBeenCalledWith("a1", { nome: "Bela" }));
    expect(await screen.findByText("salvei o nome")).toBeDefined();
  });

  it("fechar com mudança pendente pergunta antes", async () => {
    const fechou = vi.fn();
    render(<Ficha agenteId="a1" aoFechar={fechou} aoMudar={() => {}} />);
    fireEvent.change(await screen.findByLabelText("Nome"), { target: { value: "Bela" } });
    fireEvent.keyDown(document, { key: "Escape" });
    expect(fechou).not.toHaveBeenCalled();
    fireEvent.click(screen.getByRole("button", { name: "Descartar e fechar" }));
    await waitFor(() => expect(fechou).toHaveBeenCalled());
  });

  it("remover é a lixeira do rodapé, e pergunta ali mesmo antes de apagar", async () => {
    const remove = vi.spyOn(api, "removeAgente").mockResolvedValue({
      removido: true,
      canal_desconectado: false,
    });
    const fechou = vi.fn();
    render(<Ficha agenteId="a1" aoFechar={fechou} aoMudar={() => {}} />);

    fireEvent.click(await screen.findByRole("button", { name: "Remover o agente" }));
    expect(remove).not.toHaveBeenCalled();
    expect(screen.getByRole("alertdialog", { name: "Remover Bella" })).toBeDefined();

    fireEvent.click(screen.getByRole("button", { name: "Remover" }));
    await waitFor(() => expect(remove).toHaveBeenCalledWith("a1", "Bella"));
    expect(fechou).toHaveBeenCalled();
  });
});
