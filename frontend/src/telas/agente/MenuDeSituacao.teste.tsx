import { fireEvent, render, screen, waitFor } from "@testing-library/react";
import { beforeEach, describe, expect, it, vi } from "vitest";
import { api, ErroDaApi, type Agente } from "../../api/cliente";
import { MenuDeSituacao } from "./MenuDeSituacao";

const AGENTE = {
  id: "a1",
  nome: "Ana",
  situacao: "treinamento",
  canal: "chatwoot",
  avatar: null,
  avatar_cor: "ciano",
} as unknown as Agente;

function abre(agente: Agente = AGENTE, aoMudar = () => {}) {
  render(<MenuDeSituacao agente={agente} aoMudar={aoMudar} />);
  fireEvent.click(screen.getByRole("button", { name: "Ana, Em treinamento. Mudar a situação" }));
}

describe("Situação no avatar", () => {
  beforeEach(() => vi.restoreAllMocks());

  it("o avatar diz a situação e abre as três", () => {
    abre();
    expect(screen.getAllByRole("menuitemradio")).toHaveLength(3);
  });

  it("escolher salva e devolve o agente novo", async () => {
    const edita = vi.spyOn(api, "editaAgente").mockResolvedValue({ ...AGENTE, situacao: "ativo" });
    const mudou = vi.fn();
    abre(AGENTE, mudou);
    fireEvent.click(screen.getByRole("menuitemradio", { name: /^Ativo/ }));
    await waitFor(() => expect(edita).toHaveBeenCalledWith("a1", { situacao: "ativo" }));
    expect(mudou).toHaveBeenCalled();
  });

  it("sem canal externo, treinamento é a única escolha", () => {
    abre({ ...AGENTE, canal: "nativo" } as Agente);
    const opcoes = screen.getAllByRole("menuitemradio") as HTMLButtonElement[];
    expect(opcoes.map((o) => o.disabled)).toEqual([true, false, true]);
  });

  it("erro do servidor aparece na linha, sem derrubar a lista", async () => {
    vi.spyOn(api, "editaAgente").mockRejectedValue(new ErroDaApi(422, "sem canal ele fala só aqui"));
    abre();
    fireEvent.click(screen.getByRole("menuitemradio", { name: /^Ativo/ }));
    expect(await screen.findByRole("alert")).toHaveProperty(
      "textContent",
      "sem canal ele fala só aqui",
    );
  });
});
