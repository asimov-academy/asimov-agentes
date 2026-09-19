import { useEffect, useRef, useState } from "react";
import { api, ErroDaApi, type Agente, type Situacao } from "../../api/cliente";
import { Avatar } from "../../design/Avatar";
import { Icone } from "../../design/Icone";
import { SITUACAO, SITUACOES } from "./situacoes";

/** O avatar do agente na lista, que também é onde a situação se troca.
 *
 *  A bolinha no canto do retrato diz em que pé ele está, e clicar abre as três. Estava num item do
 *  menu de reticências, longe da única coisa da linha que já representa o agente inteiro.
 *
 *  Sem canal externo o agente fala só no painel, e isso é o treinamento: as outras duas aparecem
 *  apagadas, com o motivo, e o servidor também as recusa.
 */
export function MenuDeSituacao({
  agente,
  aoMudar,
}: {
  agente: Agente;
  aoMudar: (novo: Agente) => void;
}) {
  const [aberto, setAberto] = useState(false);
  const [salvando, setSalvando] = useState(false);
  const [erro, setErro] = useState("");
  const caixa = useRef<HTMLDivElement>(null);
  const atual = SITUACAO(agente.situacao);
  const semCanal = agente.canal === "nativo";

  useEffect(() => {
    if (!aberto) return;
    const fora = (e: MouseEvent) => {
      if (!caixa.current?.contains(e.target as Node)) setAberto(false);
    };
    const tecla = (e: KeyboardEvent) => e.key === "Escape" && setAberto(false);
    document.addEventListener("mousedown", fora);
    document.addEventListener("keydown", tecla);
    return () => {
      document.removeEventListener("mousedown", fora);
      document.removeEventListener("keydown", tecla);
    };
  }, [aberto]);

  async function muda(qual: Situacao) {
    setAberto(false);
    if (qual === agente.situacao) return;
    setSalvando(true);
    setErro("");
    try {
      aoMudar(await api.editaAgente(agente.id, { situacao: qual }));
    } catch (problema) {
      setErro(problema instanceof ErroDaApi ? problema.message : String(problema));
    } finally {
      setSalvando(false);
    }
  }

  return (
    <div ref={caixa} className="relative">
      <button
        onClick={() => setAberto((a) => !a)}
        disabled={salvando}
        aria-haspopup="menu"
        aria-expanded={aberto}
        aria-label={`${agente.nome}, ${atual.rotulo}. Mudar a situação`}
        title={`${atual.rotulo}. Clique para mudar`}
        className="flex h-11 w-11 items-center justify-center rounded-md transition-opacity hover:opacity-80 disabled:opacity-50"
      >
        <Avatar agente={agente} marca={atual.cor} />
      </button>

      {aberto && (
        <div
          role="menu"
          className="absolute left-0 top-full z-30 mt-1 w-72 rounded-lg border border-borda bg-panel p-1 shadow-alto"
        >
          {SITUACOES.map((s) => (
            <button
              key={s.valor}
              role="menuitemradio"
              aria-checked={s.valor === agente.situacao}
              disabled={semCanal && s.valor !== "treinamento"}
              onClick={() => muda(s.valor)}
              className="flex w-full items-start gap-2.5 rounded-md p-2.5 text-left transition-colors hover:bg-surface disabled:cursor-not-allowed disabled:opacity-40 disabled:hover:bg-transparent"
            >
              <span className={`mt-1.5 h-2 w-2 shrink-0 rounded-full ${s.cor}`} />
              <span className="min-w-0 flex-1">
                <span
                  className={`block text-sm ${s.valor === agente.situacao ? "text-texto" : "text-muted"}`}
                >
                  {s.rotulo}
                </span>
                <span className="block text-xs leading-snug text-dim">{s.explica}</span>
              </span>
              {s.valor === agente.situacao && (
                <Icone nome="act-check" tamanho={14} className="mt-1 shrink-0 text-ciano" />
              )}
            </button>
          ))}
          {/* Só o que as opções apagadas não dizem: por que elas estão apagadas. O que cada uma
              faz já está escrito nelas. */}
          {semCanal && (
            <p className="px-3 pb-1 pt-2 text-xs leading-snug text-dim">
              As outras pedem um canal conectado.
            </p>
          )}
        </div>
      )}

      {erro && (
        <p role="alert" className="absolute left-0 top-full z-20 mt-1 w-64 text-xs text-perigo">
          {erro}
        </p>
      )}
    </div>
  );
}
