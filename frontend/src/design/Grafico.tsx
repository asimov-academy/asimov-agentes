import { useId, useState } from "react";

/** A AXIS do design system (seção 2), portada para React sem biblioteca nenhuma.
 *
 *  O original é um `ChartRenderer` que desenha SVG na mão com `document.createElementNS`. Aqui o
 *  mesmo desenho sai do JSX, com as mesmas três formas que a seção usa: a curva com suavização de
 *  Bézier e os pontos por cima, a barra que cresce de baixo para cima e a rosca com o buraco em
 *  60% do raio. O que muda do original é só a paleta: lá o acento é laranja, aqui é o lime dos
 *  tokens. Cor vem de classe do Tailwind, nunca escrita no atributo.
 *
 *  O SVG usa uma caixa fixa de 1000x300 com `preserveAspectRatio="none"` na horizontal: é o que
 *  deixa o gráfico ocupar a largura do cartão sem precisar medir o elemento no navegador, coisa
 *  que no original dependia de `offsetWidth`.
 */

export type Ponto = { rotulo: string; valor: number; detalhe?: string };

const LARGURA = 1000;
const ALTURA = 300;
const RESPIRO = 24;

/** A curva do design system: dois pontos de controle na metade da distância horizontal. */
function caminhoDaCurva(pontos: { x: number; y: number }[]): string {
  return pontos.reduce((d, atual, i) => {
    if (i === 0) return `M ${atual.x},${atual.y}`;
    const antes = pontos[i - 1];
    const meio = (atual.x - antes.x) * 0.5;
    return `${d} C ${antes.x + meio},${antes.y} ${atual.x - meio},${atual.y} ${atual.x},${atual.y}`;
  }, "");
}

function escala(valor: number, teto: number): number {
  if (teto <= 0) return ALTURA - RESPIRO;
  return ALTURA - RESPIRO - (valor / teto) * (ALTURA - RESPIRO * 2);
}

export function Grafico({
  tipo,
  pontos,
  rotuloDoValor = (p) => String(p.valor),
  altura = "h-64",
}: {
  tipo: "area" | "barras" | "rosca" | "ponteiro";
  pontos: Ponto[];
  rotuloDoValor?: (p: Ponto) => string;
  altura?: string;
}) {
  const [emFoco, setEmFoco] = useState<number | null>(null);
  const id = useId();
  const teto = Math.max(...pontos.map((p) => p.valor), 1);
  const aviso = emFoco === null ? null : pontos[emFoco];
  // Rosca e ponteiro precisam manter a proporção: esticar a largura viraria elipse.
  const redonda = tipo === "rosca" || tipo === "ponteiro";

  return (
    <figure className="relative m-0 w-full">
      <svg
        viewBox={redonda ? `0 0 ${ALTURA} ${ALTURA}` : `0 0 ${LARGURA} ${ALTURA}`}
        preserveAspectRatio={redonda ? "xMidYMid meet" : "none"}
        className={`w-full ${altura} overflow-visible`}
        role="img"
        aria-labelledby={id}
      >
        <title id={id}>
          {pontos.map((p) => `${p.rotulo}: ${rotuloDoValor(p)}`).join(", ") || "sem dados"}
        </title>

        {/* As cinco réguas horizontais da AXIS, no tom `grade`. */}
        {(tipo === "area" || tipo === "barras") &&
          [0, 1, 2, 3, 4].map((i) => {
            const y = RESPIRO + (i * (ALTURA - RESPIRO * 2)) / 4;
            return (
              <line
                key={i}
                x1={0}
                x2={LARGURA}
                y1={y}
                y2={y}
                className="stroke-grade"
                strokeWidth={1}
                vectorEffect="non-scaling-stroke"
              />
            );
          })}

        {tipo === "area" && <Area pontos={pontos} teto={teto} aoFocar={setEmFoco} />}
        {tipo === "barras" && <Barras pontos={pontos} teto={teto} aoFocar={setEmFoco} />}
        {tipo === "rosca" && <Rosca pontos={pontos} aoFocar={setEmFoco} />}
        {tipo === "ponteiro" && <Ponteiro ponto={pontos[0]} rotuloDoValor={rotuloDoValor} />}
      </svg>

      {/* O `.axis-text` da AXIS: primeira, do meio e última fatia, para saber onde o gráfico
          começa e termina sem precisar passar o mouse. */}
      {!redonda && pontos.length > 1 && (
        <div className="mt-2 flex justify-between font-mono text-[0.625rem] text-muted">
          <span>{pontos[0].rotulo}</span>
          <span className="hidden sm:inline">{pontos[Math.floor(pontos.length / 2)].rotulo}</span>
          <span>{pontos[pontos.length - 1].rotulo}</span>
        </div>
      )}

      {/* O tooltip da AXIS: mono, fundo preto, borda de 1px, preso ao topo do gráfico. */}
      <figcaption
        aria-live="polite"
        className={`pointer-events-none absolute right-0 top-0 border border-borda bg-void px-3 py-1 font-mono text-xs transition-opacity ${
          aviso ? "opacity-100" : "opacity-0"
        }`}
      >
        {aviso && (
          <>
            <span className="text-muted">{aviso.rotulo}</span>{" "}
            <span className="text-lime">{rotuloDoValor(aviso)}</span>
            {aviso.detalhe && <span className="text-muted"> · {aviso.detalhe}</span>}
          </>
        )}
      </figcaption>
    </figure>
  );
}

function Area({
  pontos,
  teto,
  aoFocar,
}: {
  pontos: Ponto[];
  teto: number;
  aoFocar: (i: number | null) => void;
}) {
  const coordenadas = pontos.map((p, i) => ({
    x: pontos.length === 1 ? LARGURA / 2 : (i / (pontos.length - 1)) * LARGURA,
    y: escala(p.valor, teto),
  }));
  const curva = caminhoDaCurva(coordenadas);

  return (
    <>
      <path
        d={`${curva} L ${LARGURA},${ALTURA} L 0,${ALTURA} Z`}
        className="animate-surge fill-lime opacity-0"
        fillOpacity={0.1}
      />
      <path
        d={curva}
        fill="none"
        className="animate-traco stroke-lime [stroke-dasharray:2000] [stroke-dashoffset:2000]"
        strokeWidth={2}
        vectorEffect="non-scaling-stroke"
      />
      {coordenadas.map((c, i) => (
        <circle
          key={i}
          cx={c.x}
          cy={c.y}
          r={4}
          className="animate-surge cursor-pointer fill-surface stroke-lime opacity-0"
          strokeWidth={2}
          vectorEffect="non-scaling-stroke"
          style={{ animationDelay: `${0.5 + i * 0.03}s` }}
          onMouseEnter={() => aoFocar(i)}
          onMouseLeave={() => aoFocar(null)}
        />
      ))}
    </>
  );
}

function Barras({
  pontos,
  teto,
  aoFocar,
}: {
  pontos: Ponto[];
  teto: number;
  aoFocar: (i: number | null) => void;
}) {
  const passo = LARGURA / pontos.length;
  const largura = passo * 0.6;
  return (
    <>
      {pontos.map((p, i) => {
        const alto = (p.valor / teto) * (ALTURA - RESPIRO);
        // A última barra é a do acento no original: aqui é a fatia mais recente.
        const ultima = i === pontos.length - 1;
        return (
          <rect
            key={i}
            x={i * passo + (passo - largura) / 2}
            y={ALTURA - alto}
            width={largura}
            height={alto}
            className={`animate-cresce origin-bottom cursor-pointer transition-colors ${
              ultima ? "fill-lime hover:fill-texto" : "fill-dim hover:fill-texto"
            }`}
            style={{ animationDelay: `${i * 0.03}s` }}
            onMouseEnter={() => aoFocar(i)}
            onMouseLeave={() => aoFocar(null)}
          />
        );
      })}
    </>
  );
}

/** A rosca da AXIS: buraco em 60% do raio e uma fatia por cor da escala de cinza, com o lime na
 *  maior. Ela desenha numa caixa quadrada: esticar a largura como os outros dois viraria elipse. */
function Rosca({ pontos, aoFocar }: { pontos: Ponto[]; aoFocar: (i: number | null) => void }) {
  const total = pontos.reduce((soma, p) => soma + p.valor, 0);
  const cx = ALTURA / 2;
  const cy = ALTURA / 2;
  const raio = ALTURA / 2 - RESPIRO;
  const buraco = raio * 0.6;
  const TONS = ["fill-lime", "fill-texto", "fill-muted", "fill-dim", "fill-borda"];
  let angulo = -Math.PI / 2;

  if (total <= 0) return null;

  return (
    <>
      {pontos.map((p, i) => {
        const fatia = (p.valor / total) * Math.PI * 2;
        const fim = angulo + fatia;
        const grande = fatia > Math.PI ? 1 : 0;
        const d = [
          `M ${cx + raio * Math.cos(angulo)} ${cy + raio * Math.sin(angulo)}`,
          `A ${raio} ${raio} 0 ${grande} 1 ${cx + raio * Math.cos(fim)} ${cy + raio * Math.sin(fim)}`,
          `L ${cx + buraco * Math.cos(fim)} ${cy + buraco * Math.sin(fim)}`,
          `A ${buraco} ${buraco} 0 ${grande} 0 ${cx + buraco * Math.cos(angulo)} ${cy + buraco * Math.sin(angulo)}`,
          "Z",
        ].join(" ");
        angulo = fim;
        return (
          <path
            key={i}
            d={d}
            className={`animate-surge cursor-pointer stroke-void opacity-0 ${TONS[i % TONS.length]}`}
            strokeWidth={2}
            style={{ animationDelay: `${i * 0.08}s` }}
            onMouseEnter={() => aoFocar(i)}
            onMouseLeave={() => aoFocar(null)}
          />
        );
      })}
    </>
  );
}


/** O "GAUGE CHART" da AXIS (seção 2, cartão 7): meio arco de 10px com a ponta redonda, o trilho em
 *  `surface` e o número em mono no centro. É o formato do sistema para uma proporção que a pessoa
 *  lê de relance, sem precisar comparar com nada. */
function Ponteiro({
  ponto,
  rotuloDoValor,
}: {
  ponto: Ponto | undefined;
  rotuloDoValor: (p: Ponto) => string;
}) {
  if (!ponto) return null;
  const cx = ALTURA / 2;
  const cy = ALTURA - RESPIRO * 2;
  const raio = ALTURA / 2 - RESPIRO;
  const porcento = Math.max(0, Math.min(100, ponto.valor));
  const angulo = Math.PI - (porcento / 100) * Math.PI;
  const trilho = `M ${cx - raio} ${cy} A ${raio} ${raio} 0 0 1 ${cx + raio} ${cy}`;
  const arco = `M ${cx - raio} ${cy} A ${raio} ${raio} 0 ${porcento > 50 ? 1 : 0} 1 ${
    cx + raio * Math.cos(angulo)
  } ${cy - raio * Math.sin(angulo)}`;

  return (
    <>
      <path d={trilho} fill="none" className="stroke-borda" strokeWidth={10} strokeLinecap="round" />
      <path
        d={arco}
        fill="none"
        className="animate-traco stroke-lime drop-shadow-lime [stroke-dasharray:1000] [stroke-dashoffset:1000]"
        strokeWidth={10}
        strokeLinecap="round"
      />
      <text
        x={cx}
        y={cy - 24}
        textAnchor="middle"
        className="fill-texto font-mono text-[2rem]"
      >
        {rotuloDoValor(ponto)}
      </text>
      <text x={cx} y={cy + 24} textAnchor="middle" className="fill-dim font-mono text-[0.75rem] uppercase tracking-[0.1em]">
        {ponto.rotulo}
      </text>
    </>
  );
}
