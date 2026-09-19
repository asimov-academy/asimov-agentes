/** Regressão: salvar as duas abas preserva o comportamento. */
import { fireEvent, render, screen, waitFor } from "@testing-library/react";
import { expect, it, vi } from "vitest";
import { api, type Agente } from "../../api/cliente";
import { Ficha } from "./Ficha";

it("Trabalho preserva Comportamento no mesmo Salvar", async () => {
  Element.prototype.scrollIntoView = vi.fn();
  const agente = {
    id: "a1", nome: "Ana", situacao: "treinamento", canal: "nativo",
    empresa: "Loja Exemplo", criado_em: "2026-09-01T00:00:00Z", emojis: "nenhum",
    tom: "normal", ritmo: "natural", ferramentas: [], contatos_permitidos: [],
    perfil: { funcao: "atendimento" }, assina_nome: false,
  } as unknown as Agente;
  let persistido = "Você é Ana.";
  const ordem: string[] = [];
  vi.spyOn(api, "agente").mockResolvedValue(agente);
  vi.spyOn(api, "prompt").mockImplementation(async () => ({
    texto: persistido, gerado: persistido, perfil: agente.perfil,
  } as Awaited<ReturnType<typeof api.prompt>>));
  vi.spyOn(api, "gravaPrompt").mockImplementation(async (_id, texto) => {
    ordem.push("comportamento");
    persistido = texto;
    return { texto } as Awaited<ReturnType<typeof api.gravaPrompt>>;
  });
  vi.spyOn(api, "gravaPerfil").mockImplementation(async (_id, perfil) => {
    ordem.push("trabalho");
    // O contrato de gravaPerfil preserva texto personalizado.
    return { agente: { ...agente, perfil: { ...agente.perfil, ...perfil } }, prompt: persistido } as Awaited<ReturnType<typeof api.gravaPerfil>>;
  });
  render(<Ficha agenteId="a1" aoFechar={() => {}} aoMudar={() => {}} />);
  fireEvent.change(await screen.findByDisplayValue("Você é Ana."), {
    target: { value: "REGRA MANUAL PARA PRESERVAR" },
  });
  fireEvent.click(screen.getByRole("tab", { name: "Trabalho" }));
  fireEvent.change(await screen.findByLabelText("Quem fala com ele"), {
    target: { value: "Público novo" },
  });
  fireEvent.click(screen.getByRole("button", { name: "Salvar" }));
  await waitFor(() => expect(ordem).toEqual(["comportamento", "trabalho"]));
  expect(persistido).toContain("REGRA MANUAL PARA PRESERVAR");
  vi.restoreAllMocks();
});
