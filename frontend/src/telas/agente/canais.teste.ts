import { describe, expect, it } from "vitest";
import { CANAIS, ROTULO_DO_CANAL } from "./canais";

/** Os quatro canais que a instalação conecta hoje precisam ter texto no onboarding: sem ele o
 *  cartão não diz o que o canal serve nem o que o operador precisa ter na mão antes de começar. */
const DE_HOJE = ["chatwoot", "nativo", "waha", "whatsapp"];

describe("texto dos canais", () => {
  it("todo canal de hoje diz o que serve e o que exige", () => {
    for (const nome of DE_HOJE) {
      expect(CANAIS[nome], nome).toBeDefined();
      expect(CANAIS[nome].serve.length, nome).toBeGreaterThan(20);
      expect(CANAIS[nome].exige.length, nome).toBeGreaterThan(4);
    }
  });

  it("canal que o backend trouxer sem texto ainda aparece, com o nome cru", () => {
    expect(ROTULO_DO_CANAL("telegram")).toBe("telegram");
    expect(ROTULO_DO_CANAL("waha")).toBe("WhatsApp pelo aparelho");
  });

  it("o nome interno do canal não aparece para o operador", () => {
    expect(CANAIS.waha.rotulo).not.toContain("waha");
    expect(CANAIS.nativo.rotulo).not.toContain("nativo");
  });

  /** O terminal exige confirmar o risco da API não oficial e conta a cobrança da Meta. O painel
   *  escondia as duas coisas, e é por ele que a maioria escolhe o canal. */
  it("os dois canais com pegadinha avisam antes da escolha", () => {
    expect(CANAIS.waha.atencao).toMatch(/bloquear/i);
    expect(CANAIS.whatsapp.atencao).toMatch(/cobra/i);
    expect(CANAIS.chatwoot.atencao).toBeUndefined();
  });

  it("todo canal tem a marca para o operador reconhecer de relance", () => {
    for (const nome of DE_HOJE) expect(CANAIS[nome].marca, nome).toBeTruthy();
  });
});
