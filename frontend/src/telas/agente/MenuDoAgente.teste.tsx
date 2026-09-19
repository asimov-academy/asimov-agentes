import { fireEvent, render, screen } from "@testing-library/react";
import { describe, expect, it, vi } from "vitest";
import type { Agente } from "../../api/cliente";
import { MenuDoAgente } from "./MenuDoAgente";

const AGENTE = { id: "a1", nome: "Ana", canal: "chatwoot" } as unknown as Agente;

describe("Menu do agente", () => {
  it("abre com o que dá para fazer sem entrar na ficha", () => {
    const conversar = vi.fn();
    render(<MenuDoAgente agente={AGENTE} aoEditar={() => {}} aoConversar={conversar} />);
    fireEvent.click(screen.getByRole("button", { name: "Ações de Ana" }));
    expect(screen.getByRole("menuitem", { name: "Editar" })).toBeDefined();
    fireEvent.click(screen.getByRole("menuitem", { name: "Conversar" }));
    expect(conversar).toHaveBeenCalled();
  });

  it("a situação não fica aqui: ela mora no avatar", () => {
    render(<MenuDoAgente agente={AGENTE} aoEditar={() => {}} aoConversar={() => {}} />);
    fireEvent.click(screen.getByRole("button", { name: "Ações de Ana" }));
    expect(screen.queryAllByRole("menuitemradio")).toHaveLength(0);
  });
});
