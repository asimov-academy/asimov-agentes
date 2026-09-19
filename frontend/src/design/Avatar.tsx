import { useState } from "react";
import type { Agente } from "../api/cliente";

/** A cara do agente: a foto dele, ou a inicial do nome no fundo da cor escolhida.
 *
 *  Era a inicial numa caixa ciano, igual para todos: numa lista de dez agentes nenhum se distinguia
 *  do outro antes de ler o nome. A foto vem do que o operador enviou ou do WhatsApp pareado.
 *
 *  Foto que não carrega volta para a inicial, sem quadrado quebrado no meio da lista.
 */
const FUNDOS = {
  ciano: "border-ciano/40 bg-ciano/10 text-ciano",
  ok: "border-ok/40 bg-ok/10 text-ok",
  atencao: "border-atencao/40 bg-atencao/10 text-atencao",
  texto: "border-texto/30 bg-texto/10 text-texto",
} as const;

export function Avatar({
  agente,
  tamanho = 40,
  className = "",
  marca,
}: {
  agente: Pick<Agente, "nome" | "avatar" | "avatar_cor">;
  tamanho?: number;
  className?: string;
  /** A bolinha da situação, no canto de baixo. A borda é a do fundo, para ela não se perder na
   *  foto. Quem diz o que a cor quer dizer é quem usa o avatar, no nome do botão. */
  marca?: string;
}) {
  const [falhou, setFalhou] = useState(false);
  const lado = { width: tamanho, height: tamanho };
  const bolinha = Math.max(8, Math.round(tamanho * 0.28));

  const figura =
    agente.avatar && !falhou ? (
      <img
        src={agente.avatar}
        alt=""
        style={lado}
        onError={() => setFalhou(true)}
        className="h-full w-full rounded-md border border-borda object-cover"
      />
    ) : (
      <span
        aria-hidden="true"
        style={{ fontSize: Math.round(tamanho * 0.4) }}
        className={`flex h-full w-full items-center justify-center rounded-md border font-semibold ${
          FUNDOS[agente.avatar_cor] ?? FUNDOS.ciano
        }`}
      >
        {agente.nome.slice(0, 1).toUpperCase()}
      </span>
    );

  return (
    <span style={lado} className={`relative block shrink-0 ${className}`}>
      {figura}
      {marca && (
        <span
          aria-hidden="true"
          style={{ width: bolinha, height: bolinha }}
          className={`absolute -bottom-0.5 -right-0.5 rounded-full border-2 border-void ${marca}`}
        />
      )}
    </span>
  );
}
