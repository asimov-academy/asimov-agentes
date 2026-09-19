import { fireEvent, render, screen, waitFor } from "@testing-library/react";
import { beforeEach, describe, expect, it, vi } from "vitest";
import { api } from "../../api/cliente";
import { Teste } from "./Teste";

describe("Teste (aba Conversar)", () => {
  beforeEach(() => {
    vi.restoreAllMocks();
    Element.prototype.scrollIntoView = vi.fn();
    vi.spyOn(api, "mandaTeste").mockResolvedValue({ conversa: "c1" } as never);
    vi.spyOn(api, "leTeste").mockResolvedValue({
      mensagens: [],
      proxima: 0,
      respondendo: false,
      digitando: false,
    } as never);
  });

  it("vazio, o botão é o microfone; com texto, vira enviar", () => {
    render(<Teste agenteId="a1" agente="Bella" />);
    expect(screen.getByRole("button", { name: "Gravar áudio" })).toBeDefined();
    expect(screen.queryByRole("button", { name: "Enviar" })).toBeNull();
    fireEvent.change(screen.getByLabelText("Mensagem"), { target: { value: "oi" } });
    expect(screen.getByRole("button", { name: "Enviar" })).toBeDefined();
  });

  it("arquivo anexado vai pela rota de arquivo, com o texto de legenda", async () => {
    const manda = vi
      .spyOn(api, "mandaArquivoDeTeste")
      .mockResolvedValue({ conversa: "c1", conversa_id: "x", agendada: true });
    const { container } = render(<Teste agenteId="a1" agente="Bella" />);
    const foto = new File(["x"], "vitrine.png", { type: "image/png" });
    fireEvent.change(container.querySelector("input[type=file]") as HTMLInputElement, {
      target: { files: [foto] },
    });
    expect(screen.getByText("vitrine.png")).toBeDefined();
    fireEvent.change(screen.getByLabelText("Mensagem"), { target: { value: "tem esse?" } });
    fireEvent.click(screen.getByRole("button", { name: "Enviar" }));
    await waitFor(() => expect(manda).toHaveBeenCalledWith("a1", foto, "tem esse?", undefined));
  });

  it("Enter envia, Shift+Enter só quebra a linha", async () => {
    render(<Teste agenteId="a1" agente="Bella" />);
    const campo = screen.getByLabelText("Mensagem");
    fireEvent.change(campo, { target: { value: "oi" } });
    fireEvent.keyDown(campo, { key: "Enter", shiftKey: true });
    expect(api.mandaTeste).not.toHaveBeenCalled();
    fireEvent.keyDown(campo, { key: "Enter" });
    await waitFor(() => expect(api.mandaTeste).toHaveBeenCalledWith("a1", "oi", undefined));
  });

  it("a conversa é um log, para o leitor de tela ouvir a resposta", () => {
    render(<Teste agenteId="a1" agente="Bella" />);
    expect(screen.getByRole("log", { name: "Conversa com Bella" })).toBeDefined();
  });
});
