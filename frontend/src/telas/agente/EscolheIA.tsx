import { useEffect, useState } from "react";
import { api, type Modelos } from "../../api/cliente";
import { Campo } from "../../design/Campo";
import { Carregando } from "../../design/Carregando";
import { FormDaChave, NOME_DO_PROVEDOR as NOMES } from "./FormDaChave";

/** Provedor, chave e modelo de uma função do agente.
 *
 *  A IA é escolha de cada agente, não da instalação. A chave do provedor é pedida uma vez só: o
 *  servidor testa, guarda cifrada e nunca devolve. Daqui em diante o front só sabe que ela existe.
 *
 *  Serve o onboarding e a ficha: a aba Configurações pedia o modelo em texto cru, no formato
 *  `provedor:modelo`, enquanto este escolhedor já existia ao lado (auditoria de copy de 2026-09-18).
 */
export function EscolheIA({
  funcao,
  valor,
  aoMudar,
}: {
  funcao: "conversa" | "auxiliar" | "visao" | "transcricao";
  /** No formato `provedor:modelo`; vazio enquanto nada foi escolhido. */
  valor: string;
  aoMudar: (modelo: string) => void;
}) {
  const [catalogo, setCatalogo] = useState<Modelos | null>(null);
  const [provedor, setProvedor] = useState(valor.split(":")[0] ?? "");
  const [lista, setLista] = useState<string[] | null>(null);
  const [erro, setErro] = useState("");

  useEffect(() => {
    api.modelos().then(setCatalogo).catch((problema) => setErro(problema.message));
  }, []);

  const temChave = Boolean(catalogo?.com_chave.includes(provedor));

  useEffect(() => {
    if (!provedor || !temChave) return;
    setLista(null);
    api
      .modelosDoProvedor(provedor, funcao)
      .then(setLista)
      .catch(() => setLista([]));
  }, [provedor, temChave, funcao]);

  if (erro && !catalogo) return <p className="text-sm text-perigo">{erro}</p>;
  if (!catalogo) return <Carregando tipo="pontos" o_que="buscando os provedores" />;

  const provedores = funcao === "transcricao" ? catalogo.provedores_transcricao : catalogo.provedores;

  return (
    <div>
      <div className="flex flex-wrap gap-2">
        {provedores.map((p) => (
          <button
            key={p}
            onClick={() => {
              setProvedor(p);
              if (valor.split(":")[0] !== p) aoMudar("");
            }}
            aria-pressed={provedor === p}
            className={`rounded-md border px-4 py-2 text-sm transition-colors ${
              provedor === p ? "border-ciano bg-ciano/5 text-texto" : "border-borda text-muted hover:border-dim"
            }`}
          >
            {NOMES[p] ?? p}
            {catalogo.com_chave.includes(p) && <span className="ml-2 text-xs text-ok">chave guardada</span>}
          </button>
        ))}
      </div>

      {provedor && !temChave && (
        <div className="mt-6">
          <FormDaChave provedor={provedor} aoGuardar={() => api.modelos().then(setCatalogo)} />
        </div>
      )}

      {provedor && temChave && (
        <div className="mt-6">
          {lista === null ? (
            <Carregando tipo="pontos" o_que="buscando os modelos" />
          ) : (
            <>
              <div className="flex flex-col gap-1">
                {lista.map((m) => (
                  <button
                    key={m}
                    onClick={() => aoMudar(m)}
                    aria-pressed={valor === m}
                    className={`rounded-md border px-3 py-2 text-left font-mono text-sm transition-colors ${
                      valor === m ? "border-ciano bg-ciano/5 text-texto" : "border-borda text-muted hover:border-dim"
                    }`}
                  >
                    {m.slice(provedor.length + 1)}
                  </button>
                ))}
              </div>
              <div className="mt-4">
                <Campo
                  rotulo="Ou escreva o nome do modelo"
                  value={valor.startsWith(provedor + ":") && !lista.includes(valor) ? valor.slice(provedor.length + 1) : ""}
                  onChange={(e) => aoMudar(e.target.value.trim() ? `${provedor}:${e.target.value.trim()}` : "")}
                />
              </div>
            </>
          )}
        </div>
      )}
    </div>
  );
}
