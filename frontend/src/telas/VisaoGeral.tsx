import { useCallback, useEffect, useState } from "react";
import {
  api,
  PERIODOS,
  SemSessao,
  type Empresa,
  type HandoffAberto,
  type Periodo,
  type VisaoGeral as Dados,
} from "../api/cliente";
import { Aviso } from "../design/Aviso";
import { Botao } from "../design/Botao";
import { Cartao } from "../design/Cartao";
import { Carregando } from "../design/Carregando";
import { Grafico, type Ponto } from "../design/Grafico";
import { Progresso } from "../design/Progresso";
import { Vazio } from "../design/Vazio";

/** A Visão geral.
 *
 *  Quem abre esta tela é o operador, que já vive no terminal. Ele vem aqui para uma pergunta só:
 *  está tudo de pé e onde eu preciso agir. Por isso a tela é de triagem, não de relatório, e a
 *  ordem é veredito, depois o que espera por ele, depois o ritmo, e o dinheiro por último.
 *
 *  A hierarquia está nos tratamentos, não em seis caixas iguais: o veredito é frase grande com a
 *  régua de estado à esquerda, o que espera é uma lista que some quando não há nada, os três
 *  números vivem soltos sobre o fundo com a curva atravessando, e cartão existe só onde ele separa
 *  coisas diferentes de verdade.
 *
 *  Cor, tipo e espaçamento vêm do design system e não se discutem aqui.
 */

const NOME_DO_PERIODO: Record<Periodo, string> = { 1: "hoje", 7: "7 dias", 30: "30 dias" };
const ANTERIOR: Record<Periodo, string> = {
  1: "que ontem",
  7: "que na semana passada",
  30: "que no mês passado",
};

/** O canal escrito como a pessoa o conhece, não como a coluna do banco o guarda. */
const CANAL: Record<string, string> = {
  chatwoot: "no Chatwoot",
  whatsapp: "no WhatsApp",
  waha: "no WhatsApp",
  nativo: "na conversa de teste",
};

function dinheiro(valor: string | number): string {
  return Number(valor).toLocaleString("pt-BR", {
    style: "currency",
    currency: "USD",
    minimumFractionDigits: 2,
    maximumFractionDigits: 2,
  });
}

const numero = (valor: number) => valor.toLocaleString("pt-BR");

const hora = (iso: string) =>
  new Date(iso).toLocaleTimeString("pt-BR", { hour: "2-digit", minute: "2-digit" });

const dataEHora = (iso: string) =>
  new Date(iso).toLocaleString("pt-BR", {
    day: "2-digit",
    month: "2-digit",
    hour: "2-digit",
    minute: "2-digit",
  });

/** Quanto tempo a conversa está parada, em palavras. "há 9 horas" diz mais que um horário. */
function paradaHa(iso: string): string {
  const minutos = Math.max(0, Math.round((Date.now() - new Date(iso).getTime()) / 60000));
  if (minutos < 60) return `há ${minutos} min`;
  const horas = Math.round(minutos / 60);
  if (horas < 24) return `há ${horas} ${horas === 1 ? "hora" : "horas"}`;
  const dias = Math.round(horas / 24);
  return `há ${dias} ${dias === 1 ? "dia" : "dias"}`;
}

/** A falha dita como o operador entende. O tipo cru continua embaixo, menor: é por ele que se
 *  procura no log, mas não é ele que explica o que aconteceu. */
const FALHA: Record<string, string> = {
  turno_modelo_falhou: "O modelo de IA não respondeu",
  envio_falhou: "A mensagem não saiu",
  handoff_falhou: "Não deu para passar a conversa",
  webhook_json_invalido: "Chegou uma mensagem que não deu para ler",
  webhook_token_desconhecido: "Mensagem para um agente que não existe mais",
  canal_fora_do_ar: "O canal saiu do ar",
};

function rotuloDoPonto(iso: string, por: "hour" | "day"): string {
  const quando = new Date(iso);
  return por === "hour"
    ? quando.toLocaleTimeString("pt-BR", { hour: "2-digit", minute: "2-digit" })
    : quando.toLocaleDateString("pt-BR", { day: "2-digit", month: "2-digit" });
}

/** A frase do veredito. Em português direto, do ponto de vista de quem lê, e sempre dizendo o que
 *  está acontecendo em vez de um adjetivo de humor. */
function veredito(dados: Dados, dias: Periodo): string {
  const { falhas, handoffs_vencidos: vencidos } = dados.totais;
  if (dados.situacao.cor === "perigo") return "Um canal saiu do ar";
  if (vencidos > 0) {
    return vencidos === 1 ? "Uma conversa passou do prazo" : `${vencidos} conversas passaram do prazo`;
  }
  if (falhas > 0) {
    return falhas === 1
      ? `Uma falha ${dias === 1 ? "hoje" : `nos últimos ${NOME_DO_PERIODO[dias]}`}`
      : `${falhas} falhas ${dias === 1 ? "hoje" : `nos últimos ${NOME_DO_PERIODO[dias]}`}`;
  }
  if (dados.totais.turnos === 0) return "Nenhum agente respondeu neste período";
  return "Tudo no ar";
}

const REGUA = { ok: "border-l-ok", atencao: "border-l-atencao", perigo: "border-l-perigo" };

export function VisaoGeral({
  empresas,
  empresa,
  aoTrocarEmpresa,
  aoSaberSituacao,
}: {
  empresas: Empresa[];
  empresa: string;
  aoTrocarEmpresa: (id: string) => void;
  aoSaberSituacao: (situacao: Dados["situacao"]) => void;
}) {
  const [dias, setDias] = useState<Periodo>(7);
  const [dados, setDados] = useState<Dados | null>(null);
  const [erro, setErro] = useState("");
  const [carregando, setCarregando] = useState(true);

  const busca = useCallback(() => {
    setCarregando(true);
    setErro("");
    api
      .visaoGeral(dias, empresa || undefined)
      .then((vindo) => {
        setDados(vindo);
        aoSaberSituacao(vindo.situacao);
      })
      .catch((problema) => {
        if (problema instanceof SemSessao) throw problema;
        setErro(problema.message);
      })
      .finally(() => setCarregando(false));
  }, [dias, empresa, aoSaberSituacao]);

  useEffect(busca, [busca]);

  const esperando = !dados || carregando;

  const serie: Ponto[] =
    dados?.serie.pontos.map((p) => ({
      rotulo: rotuloDoPonto(p.quando, dados.serie.por),
      valor: p.turnos,
    })) ?? [];

  const gasto: Ponto[] =
    dados?.modelos
      .filter((m) => Number(m.custo) > 0)
      .map((m) => ({ rotulo: m.modelo, valor: Number(m.custo) })) ?? [];
  const totalGasto = gasto.reduce((soma, m) => soma + m.valor, 0);
  const maisTurnos = Math.max(...(dados?.agentes.map((a) => a.turnos) ?? [0]), 1);

  return (
    <>
      {/* O veredito. A régua de estado à esquerda é o dispositivo do design system para tom, em
          escala de título: a frase inteira fica numa cor só, e a cor mora na régua. */}
      <header
        className={`border-l-4 pl-5 ${dados ? REGUA[dados.situacao.cor] : "border-l-dim"}`}
      >
        <h1 className="max-w-[22ch] text-3xl font-semibold leading-tight tracking-tight text-texto md:text-5xl">
          {erro ? "O painel não conseguiu somar o período" : esperando ? "Somando o período" : veredito(dados, dias)}
        </h1>

        <div className="mt-6 flex flex-wrap items-center gap-3">
          <div className="flex rounded-md border border-borda p-0.5" role="group" aria-label="Período">
            {PERIODOS.map((p) => (
              <button
                key={p}
                onClick={() => setDias(p)}
                aria-pressed={p === dias}
                className={`rounded px-3.5 py-1.5 text-xs font-medium transition-colors ${
                  p === dias ? "bg-texto text-void" : "text-muted hover:text-texto"
                }`}
              >
                {NOME_DO_PERIODO[p]}
              </button>
            ))}
          </div>

          {empresas.length > 1 && (
            <select
              value={empresa}
              aria-label="Empresa"
              onChange={(e) => aoTrocarEmpresa(e.target.value)}
              className="rounded-md border border-borda bg-surface px-3 py-2 text-xs text-muted transition-colors hover:text-texto focus:border-ciano"
            >
              <option value="">Todas as empresas</option>
              {empresas.map((e) => (
                <option key={e.id} value={e.id}>
                  {e.nome}
                </option>
              ))}
            </select>
          )}
        </div>
      </header>

      {erro ? (
        <div className="mt-10">
          <Aviso tom="erro" titulo="a consulta não voltou">
            <p>{erro}</p>
            <div className="mt-4">
              <Botao icone="sys-refresh" pequeno onClick={busca}>
                Tentar de novo
              </Botao>
            </div>
          </Aviso>
        </div>
      ) : esperando ? (
        <div className="mt-16">
          <Carregando tipo="barras" o_que="somando o período" />
        </div>
      ) : (
        <>
          {/* Esperando você: some inteira quando não há nada esperando, em vez de virar um cartão
              vazio dizendo que está tudo bem. O veredito lá em cima já disse isso. */}
          {dados.handoffs.length > 0 && (
            <section className="mt-12">
              <h2 className="mb-4 text-lg font-semibold text-texto">Esperando você</h2>
              <ul className="border-t border-borda">
                {dados.handoffs.map((h) => (
                  <Espera key={h.id} handoff={h} mostrarEmpresa={!empresa} />
                ))}
              </ul>
            </section>
          )}

          {/* O ritmo. Três números soltos sobre o fundo, sem moldura, e a curva atravessando a
              largura embaixo deles. */}
          <section className="mt-16">
            <div className="grid gap-8 border-t border-borda pt-8 sm:grid-cols-3">
              <Destaque
                valor={numero(dados.totais.turnos)}
                explicacao="respostas dadas"
                variacao={dados.variacao.turnos}
                dias={dias}
              />
              <Destaque
                valor={dinheiro(dados.totais.custo)}
                explicacao="gasto com modelos"
                variacao={dados.variacao.custo}
                dias={dias}
                subirEBom={false}
                rodape={
                  dados.totais.custo_parcial
                    ? "um modelo não informou o preço: o valor verdadeiro é maior"
                    : undefined
                }
              />
              <Destaque
                valor={dados.resolucao.porcento === null ? "0%" : `${dados.resolucao.porcento}%`}
                explicacao={
                  dados.resolucao.porcento === null
                    ? "nenhuma conversa começou neste período"
                    : `das ${numero(dados.resolucao.conversas)} conversas terminaram sem chamar uma pessoa`
                }
              />
            </div>

            {dados.totais.turnos === 0 ? (
              <div className="mt-8">
                <Vazio titulo="nenhuma resposta ainda" icone="comm-chat">
                  A curva aparece na primeira resposta de um agente.
                </Vazio>
              </div>
            ) : (
              <div className="mt-8">
                <Grafico tipo="area" pontos={serie} rotuloDoValor={(p) => `${p.valor} respostas`} />
              </div>
            )}
          </section>

          {/* Duas listas diferentes, e é aqui que cartão serve para alguma coisa: separar uma da
              outra. */}
          <div className="mt-16 grid gap-6 lg:grid-cols-2">
            <Cartao titulo="Quem respondeu">
              {dados.agentes.length === 0 ? (
                <Vazio titulo="nenhum agente respondeu" icone="nav-team">
                  Crie um agente e ele aparece aqui, com as respostas e o custo.
                </Vazio>
              ) : (
                <div className="flex flex-col gap-4">
                  {dados.agentes.map((a) => (
                    <Progresso
                      key={`${a.cliente}-${a.agente}`}
                      rotulo={empresa ? a.agente : `${a.agente}, ${a.cliente}`}
                      escrita="nome"
                      valor={a.turnos}
                      de={maisTurnos}
                      escrito={`${numero(a.turnos)} respostas, ${dinheiro(a.custo)}`}
                    />
                  ))}
                </div>
              )}
            </Cartao>

            <Cartao titulo="Onde travou">
              {dados.falhas.length === 0 ? (
                <Vazio titulo="nada travou" icone="stat-success">
                  Falha de IA, de envio e de mensagem recebida aparece aqui assim que acontece.
                </Vazio>
              ) : (
                <ul className="flex flex-col divide-y divide-borda">
                  {dados.falhas.slice(0, 5).map((f, i) => (
                    <li key={i} className="flex flex-col gap-1 py-3 first:pt-0">
                      <div className="flex items-baseline justify-between gap-4">
                        <span className="text-sm text-texto">{FALHA[f.tipo] ?? f.tipo}</span>
                        <span className="shrink-0 text-[0.6875rem] text-dim">
                          {dataEHora(f.criado_em)}
                        </span>
                      </div>
                      <p className="text-sm text-muted">
                        {f.agente ? `${f.agente}, em ${f.cliente}` : "sem agente identificado"}
                      </p>
                      {f.resumo && (
                        <p className="break-words text-sm text-muted">{f.resumo}</p>
                      )}
                      <p className="tecnico text-[0.6875rem] text-dim">{f.tipo}</p>
                    </li>
                  ))}
                </ul>
              )}
            </Cartao>
          </div>

          {/* O dinheiro por último: é o que menos pede ação. Rosca à esquerda, fatia por modelo à
              direita, num cartão largo que não repete o formato dos dois de cima. */}
          <div className="mt-6">
            <Cartao titulo="Para onde foi o dinheiro">
              {gasto.length === 0 ? (
                <Vazio titulo="nada gasto no período" icone="nav-reports">
                  O custo aparece assim que um modelo informar o preço da chamada.
                </Vazio>
              ) : (
                <div className="grid items-center gap-8 md:grid-cols-[14rem_1fr]">
                  <Grafico
                    tipo="rosca"
                    pontos={gasto}
                    altura="h-44"
                    rotuloDoValor={(p) => dinheiro(p.valor)}
                  />
                  <div className="flex flex-col gap-4">
                    {dados.modelos.map((m) => (
                      <Progresso
                        key={m.modelo}
                        rotulo={m.modelo}
                        escrita="token"
                        valor={Number(m.custo)}
                        de={totalGasto}
                        escrito={`${dinheiro(m.custo)} em ${numero(m.chamadas)} chamadas`}
                      />
                    ))}
                  </div>
                </div>
              )}
            </Cartao>
          </div>

          <p className="mt-12 text-sm text-dim">
            Os mesmos números que <span className="tecnico text-muted">asimov consumo</span>{" "}
            mostra no terminal.
          </p>
        </>
      )}
    </>
  );
}

/** Uma conversa parada com uma pessoa. A régua à esquerda diz se já passou do prazo. */
function Espera({ handoff, mostrarEmpresa }: { handoff: HandoffAberto; mostrarEmpresa: boolean }) {
  return (
    <li
      className={`flex flex-wrap items-baseline justify-between gap-x-8 gap-y-2 border-b border-borda border-l-2 py-4 pl-4 ${
        handoff.vencido ? "border-l-perigo" : "border-l-transparent"
      }`}
    >
      <div className="min-w-0">
        <p className="text-base text-texto">
          {mostrarEmpresa ? `${handoff.agente}, na ${handoff.cliente}` : handoff.agente}
        </p>
        <p className="mt-0.5 text-sm text-muted">
          {CANAL[handoff.canal] ?? `no ${handoff.canal}`}, desde as {hora(handoff.iniciado_em)}
        </p>
      </div>
      {/* Sem selo: a régua vermelha e o tempo em vermelho já dizem que passou do prazo, e um
          terceiro aviso da mesma coisa só ocupa a linha no celular. */}
      <div className="flex items-baseline gap-4">
        <span className={`text-sm ${handoff.vencido ? "text-perigo" : "text-muted"}`}>
          parada {paradaHa(handoff.iniciado_em)}
        </span>
        {/* O código do jeito que se escreve no canal, com o que ele faz ao lado: sozinho, ele
            não diz onde digitar. Em Conversas existe o botão que faz o mesmo. */}
        <span className="text-sm text-dim">
          devolve ao agente com <span className="tecnico text-muted">/retomar {handoff.codigo}</span>
        </span>
      </div>
    </li>
  );
}

/** Um dos três números do ritmo: o valor em mono, o que ele quer dizer em frase, e a comparação
 *  com o período anterior. Sem rótulo em caixa alta por cima. */
function Destaque({
  valor,
  explicacao,
  variacao,
  dias,
  subirEBom = true,
  rodape,
}: {
  valor: string;
  explicacao: string;
  variacao?: number | null;
  dias?: Periodo;
  subirEBom?: boolean;
  rodape?: string;
}) {
  return (
    <div>
      {/* A escala sobe com a largura: em mono, "US$ 1.234,56" em 5xl não cabe numa coluna de um
          terço de tela média, e passa por cima do número do lado. */}
      <p className="font-mono text-3xl leading-none text-texto md:text-4xl lg:text-5xl">{valor}</p>
      <p className="mt-3 max-w-[28ch] text-sm leading-snug text-muted">{explicacao}</p>
      {variacao !== undefined && dias !== undefined && (
        <Comparacao valor={variacao} dias={dias} subirEBom={subirEBom} />
      )}
      {rodape && <p className="mt-1 max-w-[30ch] text-sm leading-snug text-dim">{rodape}</p>}
    </div>
  );
}

function Comparacao({
  valor,
  dias,
  subirEBom,
}: {
  valor: number | null;
  dias: Periodo;
  subirEBom: boolean;
}) {
  if (valor === null) {
    return <p className="mt-2 text-sm text-dim">sem período anterior para comparar</p>;
  }
  const parado = Math.abs(valor) < 0.5;
  const bom = valor > 0 === subirEBom;
  const cor = parado ? "text-muted" : bom ? "text-ok" : "text-perigo";
  return (
    <p className={`mt-2 text-sm ${cor}`}>
      {parado ? `igual ${ANTERIOR[dias]}` : `${valor > 0 ? "+" : ""}${valor.toFixed(0)}% ${ANTERIOR[dias]}`}
    </p>
  );
}
