import { useState } from "react";
import { api, ErroDaApi } from "../../api/cliente";
import { Botao } from "../../design/Botao";
import { Campo } from "../../design/Campo";

export const NOME_DO_PROVEDOR: Record<string, string> = {
  openai: "OpenAI",
  anthropic: "Anthropic",
  gemini: "Gemini",
  groq: "Groq",
};

/** A chave de API de um provedor. Vai e nunca volta: o backend testa no provedor, guarda cifrada e
 *  daí em diante o front só sabe que ela existe. */
export function FormDaChave({ provedor, aoGuardar }: { provedor: string; aoGuardar: () => void }) {
  const [chave, setChave] = useState("");
  const [erro, setErro] = useState("");
  const [testando, setTestando] = useState(false);
  const nome = NOME_DO_PROVEDOR[provedor] ?? provedor;

  async function guarda() {
    setErro("");
    setTestando(true);
    try {
      await api.guardaChave(provedor, chave.trim());
      setChave("");
      aoGuardar();
    } catch (problema) {
      setErro(problema instanceof ErroDaApi ? problema.message : String(problema));
    } finally {
      setTestando(false);
    }
  }

  return (
    <div>
      <Campo
        rotulo={`Chave de API da ${nome}`}
        type="password"
        autoComplete="off"
        value={chave}
        onChange={(e) => setChave(e.target.value)}
        erro={erro || undefined}
      />
      <p className="mt-2 text-sm text-dim">
        Pedida uma vez: vale para todo agente que usar a {nome} e fica cifrada no servidor.
      </p>
      <div className="mt-4">
        <Botao pequeno tom="solido" disabled={!chave.trim() || testando} onClick={guarda}>
          {testando ? "Testando a chave" : "Testar e guardar"}
        </Botao>
      </div>
    </div>
  );
}
