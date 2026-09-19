import { fireEvent, render, screen } from "@testing-library/react";
import { describe, expect, it } from "vitest";
import type { Agente } from "../api/cliente";
import { Avatar } from "./Avatar";

const ANA = { nome: "ana", avatar: null, avatar_cor: "ok" } as unknown as Agente;

describe("Avatar", () => {
  it("sem foto, é a inicial do nome na cor do agente", () => {
    const { container } = render(<Avatar agente={ANA} />);
    expect(container.textContent).toBe("A");
    expect(container.querySelector("span span")?.className).toContain("bg-ok/10");
  });

  it("a bolinha da situação entra no canto quando pedem", () => {
    const { container } = render(<Avatar agente={ANA} marca="bg-atencao" />);
    expect(container.querySelector(".bg-atencao")).not.toBeNull();
    expect(render(<Avatar agente={ANA} />).container.querySelector(".bg-atencao")).toBeNull();
  });

  it("com foto, desenha a foto; se ela falhar, volta para a inicial", () => {
    const { container } = render(
      <Avatar agente={{ ...ANA, avatar: "/painel/api/agentes/a1/avatar?v=1" }} />,
    );
    const foto = screen.getByRole("presentation", { hidden: true });
    expect(foto.getAttribute("src")).toBe("/painel/api/agentes/a1/avatar?v=1");
    fireEvent.error(foto);
    expect(container.textContent).toBe("A");
  });
});
