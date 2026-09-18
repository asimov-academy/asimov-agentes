import type { ReactElement } from "react";

/** Os estados de carregando do KINETIC (design system, seção 3, "01 / Loading States").
 *
 *  Cada lugar da tela espera com a forma que combina com o que vai aparecer ali, como no original:
 *
 *  - `anel`: o Ring, traço que corre em volta do círculo. É a espera da tela inteira.
 *  - `barras`: o Bars, três traços subindo e descendo. Espera de gráfico de ritmo.
 *  - `pontos`: o Dots, três bolinhas pulando. Espera de lista.
 *  - `pulso`: o Pulse, o radar com dois anéis saindo do centro. Espera de situação e de canal.
 *  - `porcento`: o Percent, o arco que enche. Espera de número e de proporção.
 *  - `digitando`: o Typing, a janelinha com três pontos piscando. Espera de resposta do agente.
 *
 *  As animações são as do original, escritas em SMIL dentro do próprio SVG (`<animate>`) ou nos
 *  keyframes `radar` e `anel` do `tailwind.config.ts`. Cor sempre por classe, nunca no atributo.
 */
export type Espera = "anel" | "barras" | "pontos" | "pulso" | "porcento" | "digitando";

export function Carregando({
  tipo = "anel",
  o_que = "carregando",
  mudo,
  compacto,
}: {
  tipo?: Espera;
  o_que?: string;
  /** Sem o rótulo embaixo: para caber dentro de um cartão que já tem título. */
  mudo?: boolean;
  /** Metade do tamanho e sem respiro: para caber dentro de uma bolha de conversa ou de um botão. */
  compacto?: boolean;
}) {
  return (
    <div
      className={`flex items-center justify-center gap-3 ${compacto ? "[&_svg]:h-5 [&_svg]:w-5 [&>div]:h-6 [&>div]:w-6" : "flex-col py-8"}`}
      role="status"
      aria-live="polite"
    >
      {DESENHO[tipo]}
      {mudo || compacto ? (
        <span className="sr-only">{o_que}</span>
      ) : (
        <span className="rotulo">{o_que}</span>
      )}
    </div>
  );
}

const DESENHO: Record<Espera, ReactElement> = {
  // 5. RING (DASH)
  anel: (
    <svg viewBox="25 25 50 50" className="h-10 w-10 animate-[spin_2s_linear_infinite]" fill="none">
      <circle cx="50" cy="50" r="20" className="stroke-dim" strokeWidth={4} />
      <circle
        cx="50"
        cy="50"
        r="20"
        className="animate-anel stroke-ciano"
        strokeWidth={4}
        strokeLinecap="round"
      />
    </svg>
  ),

  // 4. BARS
  barras: (
    <svg viewBox="0 0 40 40" className="h-10 w-10 stroke-ciano" strokeWidth={2} strokeLinecap="round">
      {[12, 20, 28].map((x, i) => (
        <line key={x} x1={x} x2={x} y1={15} y2={25}>
          <animate attributeName="y1" dur="0.6s" begin={`${i * 0.1}s`} repeatCount="indefinite" values="15;10;15" />
          <animate attributeName="y2" dur="0.6s" begin={`${i * 0.1}s`} repeatCount="indefinite" values="25;30;25" />
        </line>
      ))}
    </svg>
  ),

  // 2. DOTS
  pontos: (
    <svg viewBox="0 0 40 40" className="h-10 w-10 fill-texto">
      {[10, 20, 30].map((cx, i) => (
        <circle key={cx} cx={cx} cy={20} r={3}>
          <animate attributeName="cy" dur="0.6s" begin={`${i * 0.1}s`} repeatCount="indefinite" values="20;15;20" />
        </circle>
      ))}
    </svg>
  ),

  // 3. PULSE (RADAR)
  pulso: (
    <div className="relative flex h-12 w-12 items-center justify-center">
      <span className="absolute z-10 h-3 w-3 rounded-full bg-ciano drop-shadow-ciano" />
      <span className="absolute h-full w-full animate-radar rounded-full border border-ciano opacity-0" />
      <span className="absolute h-full w-full animate-radar rounded-full border border-ciano opacity-0 [animation-delay:0.6s]" />
    </div>
  ),

  // 10. PROGRESS (PERCENT)
  porcento: (
    <svg viewBox="0 0 40 40" className="h-10 w-10 -rotate-90" fill="none">
      <circle cx="20" cy="20" r="16" className="stroke-borda" strokeWidth={4} />
      <circle cx="20" cy="20" r="16" className="stroke-texto" strokeWidth={4} strokeDasharray={100}>
        <animate
          attributeName="stroke-dashoffset"
          dur="2s"
          repeatCount="indefinite"
          calcMode="spline"
          keySplines="0.16 1 0.3 1"
          values="100; 20"
        />
      </circle>
    </svg>
  ),

  // 8. TYPING
  digitando: (
    <svg viewBox="0 0 24 24" className="h-10 w-10">
      <rect x={2} y={6} width={20} height={12} rx={2} fill="none" className="stroke-dim" strokeWidth={1.5} />
      {[8, 12, 16].map((cx, i) => (
        <circle key={cx} cx={cx} cy={12} r={1} className="fill-texto">
          <animate attributeName="opacity" dur="1.5s" begin={`${i * 0.2}s`} repeatCount="indefinite" values="0;1;0" />
        </circle>
      ))}
    </svg>
  ),
};
