import { beforeEach, describe, expect, it, vi } from "vitest";
import { api, ErroDaApi, guardaCsrf, SemSessao } from "./cliente";

function resposta(corpo: unknown, status = 200) {
  return Promise.resolve({
    ok: status >= 200 && status < 300,
    status,
    json: () => Promise.resolve(corpo),
  } as Response);
}

describe("cliente da API", () => {
  beforeEach(() => {
    vi.restoreAllMocks();
  });

  it("sessão vencida vira SemSessao, para o front voltar ao login", async () => {
    vi.stubGlobal(
      "fetch",
      vi.fn(() => resposta({ detail: "entre no painel" }, 401)),
    );
    await expect(api.eu()).rejects.toBeInstanceOf(SemSessao);
  });

  it("erro da API carrega o código e a referência do log", async () => {
    vi.stubGlobal(
      "fetch",
      vi.fn(() => resposta({ detail: "erro interno", referencia: "abc123" }, 500)),
    );
    await expect(api.eu()).rejects.toMatchObject({ codigo: 500, referencia: "abc123" });
    await expect(api.eu()).rejects.toBeInstanceOf(ErroDaApi);
  });

  it("leitura não manda CSRF e vai com o cookie da mesma origem", async () => {
    const espiao = vi.fn(() => resposta({ empresas: 0 }));
    vi.stubGlobal("fetch", espiao);
    guardaCsrf("token-de-escrita");
    await api.eu();
    const [caminho, opcoes] = espiao.mock.calls[0] as unknown as [string, RequestInit];
    expect(caminho).toBe("/painel/api/eu");
    expect(opcoes.credentials).toBe("same-origin");
    expect(opcoes.headers).not.toHaveProperty("X-Painel-CSRF");
  });
});
