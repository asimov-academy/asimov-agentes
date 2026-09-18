import { render, screen, fireEvent } from "@testing-library/react";
import { describe, expect, it } from "vitest";
import type { Agente } from "../../api/cliente";
import { Treinamento } from "./Treinamento";

const AGENTE = { id: "a1", nome: "Bella" } as unknown as Agente;

describe("Treinamento", () => {
  it("mostra as cinco formas de ensinar, e diz que ainda não funciona", () => {
    render(<Treinamento agente={AGENTE} />);
    for (const aba of ["Texto", "Site", "Vídeo", "Documento", "Base de conhecimento"]) {
      expect(screen.getByRole("button", { name: aba })).toBeDefined();
    }
    expect(screen.getByText("em breve")).toBeDefined();
  });

  it("trocar de aba troca o que a tela explica", () => {
    render(<Treinamento agente={AGENTE} />);
    expect(screen.getByText("Ensinar por frase")).toBeDefined();
    fireEvent.click(screen.getByRole("button", { name: "Documento" }));
    expect(screen.getByText("Ensinar por documento")).toBeDefined();
  });
});
