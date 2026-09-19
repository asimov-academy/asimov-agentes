import { render, screen, fireEvent, waitFor } from "@testing-library/react";
import { beforeEach, describe, expect, it, vi } from "vitest";
import { api, type Agente, type BaseDoAgente } from "../../api/cliente";
import { Treinamento } from "./Treinamento";

const AGENTE = { id: "a1", nome: "Bella" } as unknown as Agente;

function base(partes: Partial<BaseDoAgente> = {}): BaseDoAgente {
  return { documentos: [], modelo_embeddings: "openai:text-embedding-3-small", ...partes };
}

describe("Treinamento", () => {
  beforeEach(() => {
    vi.restoreAllMocks();
    vi.spyOn(api, "documentos").mockResolvedValue(base());
  });

  it("mostra as cinco formas de ensinar, e duas ainda não funcionam", async () => {
    render(<Treinamento agente={AGENTE} />);
    for (const aba of ["Texto", "Site", "Vídeo", "Documento", "Base compartilhada"]) {
      expect(screen.getByRole("button", { name: aba })).toBeDefined();
    }
    fireEvent.click(screen.getByRole("button", { name: "Vídeo" }));
    expect(screen.getByText("em breve")).toBeDefined();
  });

  it("trocar de aba troca o que a tela explica", async () => {
    render(<Treinamento agente={AGENTE} />);
    expect(screen.getByText("Ensinar por frase")).toBeDefined();
    fireEvent.click(screen.getByRole("button", { name: "Documento" }));
    expect(screen.getByText("Ensinar por documento")).toBeDefined();
  });

  it("uma frase vai para a API e a lista é relida", async () => {
    const ensinou = vi.spyOn(api, "enviaTexto").mockResolvedValue({
      id: "d1",
      nome: "Não entregamos fora do estado",
      origem: "texto",
      status: "pronto",
      erro: "",
      total_trechos: 1,
      criado_em: "2026-09-18T12:00:00Z",
    });
    render(<Treinamento agente={AGENTE} />);

    fireEvent.change(screen.getByLabelText(/o que o agente precisa saber/i), {
      target: { value: "Não entregamos fora do estado" },
    });
    fireEvent.click(screen.getByRole("button", { name: /ensinar/i }));

    await waitFor(() =>
      expect(ensinou).toHaveBeenCalledWith("a1", "Não entregamos fora do estado"),
    );
  });

  it("sem chave de embeddings, a tela avisa antes de o operador mandar material", async () => {
    vi.spyOn(api, "documentos").mockResolvedValue(base({ modelo_embeddings: "" }));
    render(<Treinamento agente={AGENTE} />);
    await waitFor(() =>
      expect(screen.getByText(/falta a chave de uma IA/i)).toBeDefined(),
    );
  });

  it("o material que já existe aparece com o estado dele", async () => {
    vi.spyOn(api, "documentos").mockResolvedValue(
      base({
        documentos: [
          {
            id: "d1",
            nome: "tabela-de-precos.pdf",
            origem: "documento",
            status: "erro",
            erro: "o arquivo não tem texto",
            total_trechos: 0,
            criado_em: "2026-09-18T12:00:00Z",
          },
        ],
      }),
    );
    render(<Treinamento agente={AGENTE} />);
    await waitFor(() => expect(screen.getByText("tabela-de-precos.pdf")).toBeDefined());
    expect(screen.getByText(/o arquivo não tem texto/)).toBeDefined();
  });
});
