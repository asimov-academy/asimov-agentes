import { fireEvent, render, screen } from "@testing-library/react";
import { describe, expect, it, vi } from "vitest";
import { Modal } from "./Modal";

describe("Modal", () => {
  it("é um diálogo com nome, para o leitor de tela anunciar o que abriu", () => {
    render(
      <Modal titulo="Novo agente" aoFechar={() => {}}>
        conteúdo
      </Modal>,
    );
    expect(screen.getByRole("dialog", { name: "Novo agente" })).toBeDefined();
  });

  it("Esc fecha", () => {
    const fechou = vi.fn();
    render(
      <Modal titulo="Novo agente" aoFechar={fechou}>
        conteúdo
      </Modal>,
    );
    fireEvent.keyDown(document, { key: "Escape" });
    expect(fechou).toHaveBeenCalled();
  });

  it("clicar no fundo embaçado fecha", () => {
    const fechou = vi.fn();
    const { container } = render(
      <Modal titulo="Novo agente" aoFechar={fechou}>
        conteúdo
      </Modal>,
    );
    const fundo = container.querySelector("[aria-hidden=true]") as HTMLElement;
    expect(fundo.className).toContain("backdrop-blur");
    fireEvent.click(fundo);
    expect(fechou).toHaveBeenCalled();
  });

  it("a página para de rolar enquanto ele está aberto, e volta ao fechar", () => {
    const { unmount } = render(
      <Modal titulo="Novo agente" aoFechar={() => {}}>
        conteúdo
      </Modal>,
    );
    expect(document.body.style.overflow).toBe("hidden");
    unmount();
    expect(document.body.style.overflow).not.toBe("hidden");
  });
});
