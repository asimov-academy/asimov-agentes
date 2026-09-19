import { useEffect, useRef, useState } from "react";
import type { Agente } from "../../api/cliente";
import { BotaoIcone } from "../../design/BotaoIcone";
import { Icone } from "../../design/Icone";

/** O menu da linha do agente: o que dá para fazer sem abrir a ficha.
 *
 *  Abrir e conversar são o que o operador faz o dia todo, e os dois estavam a dois cliques dentro
 *  do popup. A situação saiu daqui para o avatar, que é o que representa o agente na linha.
 *  Remover continua só na ficha: apagar agente não é coisa de menu de lista.
 */
export function MenuDoAgente({
  agente,
  aoEditar,
  aoConversar,
}: {
  agente: Agente;
  aoEditar: () => void;
  aoConversar: () => void;
}) {
  const [aberto, setAberto] = useState(false);
  const caixa = useRef<HTMLDivElement>(null);

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

  return (
    <div ref={caixa} className="relative">
      <BotaoIcone
        icone="sys-mais"
        rotulo={`Ações de ${agente.nome}`}
        aria-haspopup="menu"
        aria-expanded={aberto}
        onClick={() => setAberto((a) => !a)}
      />

      {aberto && (
        <div
          role="menu"
          className="absolute right-0 top-full z-30 mt-1 w-72 rounded-lg border border-borda bg-panel p-1 shadow-alto"
        >
          <Item
            icone="act-edit"
            rotulo="Editar"
            aoIr={() => {
              setAberto(false);
              aoEditar();
            }}
          />
          <Item
            icone="comm-chat"
            rotulo="Conversar"
            aoIr={() => {
              setAberto(false);
              aoConversar();
            }}
          />

        </div>
      )}

    </div>
  );
}

function Item({
  icone,
  rotulo,
  aoIr,
}: {
  icone: "act-edit" | "comm-chat";
  rotulo: string;
  aoIr: () => void;
}) {
  return (
    <button
      role="menuitem"
      onClick={aoIr}
      className="flex min-h-11 w-full items-center gap-2.5 rounded-md px-3 text-left text-sm text-muted transition-colors hover:bg-surface hover:text-texto"
    >
      <Icone nome={icone} tamanho={16} className="shrink-0" />
      {rotulo}
    </button>
  );
}
