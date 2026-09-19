import { useCallback, useEffect, useRef, useState } from "react";
import {
  api,
  ErroDaApi,
  type Agente,
  type CorDeAvatar,
  type EdicaoDoAgente,
  type Ferramenta,
  type Modelos,
  type NivelDeEmoji,
  type TomDeVoz,
  type Prompt,
} from "../../api/cliente";
import { Aviso } from "../../design/Aviso";
import { Botao } from "../../design/Botao";
import { BotaoIcone } from "../../design/BotaoIcone";
import { Campo } from "../../design/Campo";
import { Faixa } from "../../design/Faixa";
import { Carregando } from "../../design/Carregando";
import { Icone } from "../../design/Icone";
import type { ICONES } from "../../design/icones";
import { Interruptor } from "../../design/Interruptor";
import { Modal } from "../../design/Modal";
import { Selo } from "../../design/Selo";
import { Canal } from "./Canal";
import { Foto } from "./Foto";
import { EscolheIA } from "./EscolheIA";
import { ROTULO_DO_CANAL } from "./canais";
import { Treinamento } from "./Treinamento";

/** A ficha do agente, no mesmo popup do onboarding: a lista fica embaçada atrás.
 *
 *  Oito abas e **um salvar só**, no rodapé do popup. A aba visitada continua montada, então o que
 *  o operador mexeu numa aba fica guardado enquanto ele anda pelas outras, e o Salvar manda tudo de
 *  uma vez. Ele diz o que mudou, não um "pronto" genérico: quem mexeu em três campos quer saber
 *  quais três foram para o banco. Eram oito botões de salvar, um por aba (v0.27).
 *
 *  A sexta aba é Conversar: falar com o agente é o jeito de conferir uma mudança antes de ela
 *  chegar em alguém, e isso pertence ao agente, não à lista de conversas.
 */

// A ordem é a de montar um agente: quem ele é, o que ele faz, como ele fala, o que ele sabe, o que
// ele usa, por onde atende e, por último, o motor. Conversar saiu daqui: virou um item do menu da
// lista, porque falar com o agente não é configurá-lo.
const ABAS = [
  "perfil",
  "trabalho",
  "comunicacao",
  "treinamento",
  "ferramentas",
  "canais",
  "configuracoes",
] as const;
type Aba = (typeof ABAS)[number];

const NOME_DA_ABA: Record<Aba, string> = {
  perfil: "Perfil",
  trabalho: "Trabalho",
  comunicacao: "Comunicação",
  treinamento: "Treinamento",
  ferramentas: "Ferramentas",
  canais: "Canais",
  configuracoes: "Configurações",
};

/** O que cada preset escreve em espera, velocidade e teto do digitando. São os mesmos números do
 *  servidor (`conversas/ritmo.py`), aqui só para a tela mostrar o resultado antes de salvar. */
const NUMEROS_DO_RITMO: Record<string, [number, number, number]> = {
  instantaneo: [2, 30, 1],
  natural: [8, 6, 20],
  reflexivo: [15, 4, 25],
};

const RITMOS: { valor: string; rotulo: string; explica: string }[] = [
  { valor: "instantaneo", rotulo: "Instantâneo", explica: "Responde na hora, sem esperar." },
  { valor: "natural", rotulo: "Natural", explica: "Lê, digita e responde como uma pessoa." },
  { valor: "reflexivo", rotulo: "Reflexivo", explica: "Espera mais e escreve devagar." },
];

const TONS: { valor: TomDeVoz; rotulo: string; explica: string }[] = [
  { valor: "formal", rotulo: "Formal", explica: "Português correto, sem gíria." },
  { valor: "normal", rotulo: "Normal", explica: "Como alguém da empresa no WhatsApp." },
  { valor: "descontraido", rotulo: "Descontraído", explica: "Leve e próximo, sem perder o profissional." },
];

type Emoji = NivelDeEmoji | "livre";

const EMOJIS: { valor: Emoji; rotulo: string }[] = [
  { valor: "nenhum", rotulo: "Nenhum" },
  { valor: "pouco", rotulo: "Pouco" },
  { valor: "medio", rotulo: "Médio" },
  { valor: "muito", rotulo: "Muito" },
];

/** `livre` é o agente criado antes da escolha existir: entra na faixa só para ele. */
const EMOJIS_COM_LIVRE: { valor: Emoji; rotulo: string }[] = [
  { valor: "livre", rotulo: "Como quiser" },
  ...EMOJIS,
];

/** O ícone de cada ferramenta do catálogo. Ferramenta nova sem ícone aqui entra com o genérico:
 *  a lista do painel nunca depende de alguém lembrar de mexer neste mapa. */
const ICONE_DA_FERRAMENTA: Record<string, keyof typeof ICONES> = {
  calculadora: "cont-calc",
  busca_web: "sys-search",
  base_conhecimento: "cont-doc",
};

/** Quanto tempo a conversa fica com a pessoa antes de o agente voltar sozinho. Sem prazo é zero:
 *  a conversa espera alguém devolver. */
const PRAZOS = [
  { horas: 0, rotulo: "Sem prazo: só quando alguém devolver" },
  { horas: 1, rotulo: "1 hora" },
  { horas: 2, rotulo: "2 horas" },
  { horas: 4, rotulo: "4 horas" },
  { horas: 8, rotulo: "8 horas" },
  { horas: 24, rotulo: "1 dia" },
  { horas: 48, rotulo: "2 dias" },
  { horas: 168, rotulo: "1 semana" },
];

const FUNCOES = [
  { valor: "atendimento", rotulo: "Atendimento" },
  { valor: "suporte", rotulo: "Suporte" },
  { valor: "vendas", rotulo: "Vendas" },
] as const;

/** O que cada campo se chama quando o salvar diz o que mudou. Todo campo de `EdicaoDoAgente` tem
 *  o nome dele aqui, e um teste confere: faltando um, o operador lia "salvei restringe_temas". */
const NOME_DO_CAMPO: Record<keyof EdicaoDoAgente, string> = {
  nome: "o nome",
  situacao: "a situação",
  avatar_cor: "a cor",
  tom: "o tom",
  transfere_para_humano: "passar para uma pessoa",
  restringe_temas: "falar só de assuntos da empresa",
  memoria_ativa: "lembrar de cada contato",
  avisa_que_e_ia: "avisar que é um assistente virtual",
  aviso_de_ia: "o texto do aviso de IA",
  ritmo: "o ritmo",
  handoff_destino: "quem recebe a conversa",
  emojis: "o nível de emoji",
  max_mensagens_por_resposta: "as partes da resposta",
  buffer_segundos: "o tempo de espera",
  digitacao_caracteres_por_segundo: "a velocidade de digitação",
  digitacao_maximo_segundos: "o tempo máximo digitando",
  ferramentas: "as ferramentas",
  contatos_permitidos: "quem ele atende",
  retomada_automatica_horas: "o prazo para ele voltar",
  modelo_conversa: "o modelo de conversa",
  modelo_fallback: "o modelo reserva",
  modelo_auxiliar: "o modelo do resumo",
  modelo_visao: "o modelo de imagem",
  modelo_transcricao: "o modelo de áudio",
};


export function Ficha({
  agenteId,
  aoFechar,
  aoMudar,
  abaInicial = "perfil",
}: {
  agenteId: string;
  aoFechar: () => void;
  aoMudar: () => void;
  /** Quem vem do fim do onboarding cai direto no que escolheu fazer, não no começo da ficha. */
  abaInicial?: Aba;
}) {
  const [agente, setAgente] = useState<Agente | null>(null);
  const [aba, setAba] = useState<Aba>(abaInicial);
  const [erro, setErro] = useState("");
  // Erro de rede não é fim de linha: mudar isto refaz a busca sem fechar e reabrir o popup.
  const [tentativa, setTentativa] = useState(0);
  useEffect(() => {
    let vivo = true;
    setErro("");
    api
      .agente(agenteId)
      .then((a) => vivo && setAgente(a))
      .catch((problema) => vivo && setErro(problema.message));
    return () => {
      vivo = false;
    };
  }, [agenteId, tentativa]);

  const atualiza = useCallback(
    (novo: Agente) => {
      setAgente(novo);
      aoMudar();
    },
    [aoMudar],
  );

  // O que cada aba tem pendente, e como ela salva. A função mora em ref porque muda a cada
  // desenho da aba, e a ficha só precisa da última na hora do clique.
  const [sujas, setSujas] = useState<Partial<Record<Aba, boolean>>>({});
  const salvadores = useRef<Partial<Record<Aba, () => Promise<string>>>>({});
  const [visitadas, setVisitadas] = useState<Aba[]>([abaInicial]);
  const [versao, setVersao] = useState(0);
  const [saindo, setSaindo] = useState(false);
  const [removendo, setRemovendo] = useState<"perguntando" | "indo" | null>(null);
  const [erroRemover, setErroRemover] = useState("");
  const [salvando, setSalvando] = useState(false);
  const [feito, setFeito] = useState("");
  const [erroAoSalvar, setErroAoSalvar] = useState("");
  const sujo = Object.values(sujas).some(Boolean);
  const sujoAgora = useRef(false);
  sujoAgora.current = sujo;

  const aoSujar = useCallback(
    (qual: Aba, sujo: boolean) =>
      setSujas((antes) => (Boolean(antes[qual]) === sujo ? antes : { ...antes, [qual]: sujo })),
    [],
  );
  const registra = useCallback((qual: Aba, salva: (() => Promise<string>) | null) => {
    if (salva) salvadores.current[qual] = salva;
    else delete salvadores.current[qual];
  }, []);

  // Estável de propósito: o `Modal` refaz o foco quando o `aoFechar` muda de identidade.
  const fecha = useCallback(() => {
    if (sujoAgora.current) setSaindo(true);
    else aoFechar();
  }, [aoFechar]);

  function troca(para: Aba) {
    setAba(para);
    setVisitadas((antes) => (antes.includes(para) ? antes : [...antes, para]));
  }

  // Descartar remonta as abas: os campos voltam ao que está no banco.
  function descarta() {
    setSujas({});
    salvadores.current = {};
    setVisitadas([aba]);
    setVersao((v) => v + 1);
    setFeito("");
    setErroAoSalvar("");
  }

  async function remove() {
    setRemovendo("indo");
    setErroRemover("");
    try {
      // A API confere o nome, que é a trava do terminal. Aqui a trava é o segundo clique.
      await api.removeAgente(agenteId, agente?.nome ?? "");
      aoMudar();
      aoFechar();
    } catch (problema) {
      setErroRemover(problema instanceof ErroDaApi ? problema.message : String(problema));
      setRemovendo("perguntando");
    }
  }

  async function salvaTudo() {
    setSalvando(true);
    setErroAoSalvar("");
    setFeito("");
    const salvas: string[] = [];
    try {
      for (const qual of ABAS) {
        if (!sujas[qual]) continue;
        // Lida a cada volta: a aba anterior acabou de trocar o agente, e esta já se redesenhou.
        const salva = salvadores.current[qual];
        if (salva) salvas.push(await salva());
      }
      setFeito(`salvei ${salvas.filter(Boolean).join(", ")}`);
    } catch (problema) {
      const motivo = problema instanceof Error ? problema.message : String(problema);
      setErroAoSalvar(salvas.length ? `${motivo} (o resto foi salvo)` : motivo);
    } finally {
      setSalvando(false);
    }
  }

  /** As abas moram no cabeçalho do popup: lá elas ficam paradas enquanto o corpo rola, e não
   *  gastam uma faixa do espaço útil. O `-mb-px` encosta a linha da aba ativa na borda do
   *  cabeçalho. */
  const ABAS_NO_CABECALHO = (
    <nav
      className="-mb-px flex gap-1 overflow-x-auto"
      role="tablist"
      aria-label="Seções do agente"
      onKeyDown={(e) => {
        if (e.key !== "ArrowRight" && e.key !== "ArrowLeft") return;
        const passo = e.key === "ArrowRight" ? 1 : -1;
        const para = ABAS[(ABAS.indexOf(aba) + passo + ABAS.length) % ABAS.length];
        troca(para);
        document.getElementById(`aba-${para}`)?.focus();
      }}
    >
      {ABAS.map((a) => (
        <button
          key={a}
          id={`aba-${a}`}
          role="tab"
          aria-selected={aba === a}
          aria-controls={`painel-${a}`}
          tabIndex={aba === a ? 0 : -1}
          onClick={() => troca(a)}
          className={`flex items-center gap-1.5 whitespace-nowrap border-b-2 px-4 py-3 text-sm transition-colors ${
            aba === a
              ? "border-b-ciano text-ciano"
              : "border-b-transparent text-muted hover:text-texto"
          }`}
        >
          {NOME_DA_ABA[a]}
          {sujas[a] && (
            <span className="h-1.5 w-1.5 rounded-full bg-atencao">
              <span className="sr-only">, com mudança não salva</span>
            </span>
          )}
        </button>
      ))}
    </nav>
  );

  return (
    <Modal
      titulo={agente?.nome ?? "Agente"}
      subtitulo={
        agente ? `${ROTULO_DO_CANAL(agente.canal)}, em ${agente.empresa}` : "abrindo a ficha"
      }
      aoFechar={fecha}
      abas={agente ? ABAS_NO_CABECALHO : undefined}
      rodape={
        !agente ? undefined : removendo ? (
          // Perguntar no próprio rodapé, como o descarte: um popup por cima do popup para uma
          // pergunta de uma linha é caixa dentro de caixa.
          <div
            role="alertdialog"
            aria-label={`Remover ${agente.nome}`}
            className="flex w-full flex-wrap items-center justify-between gap-3"
          >
            <span className={`min-w-0 text-sm ${erroRemover ? "text-perigo" : "text-muted"}`}>
              {erroRemover ||
                `Remover ${agente.nome}? Ele para de atender e o endereço do canal deixa de valer. As conversas e o consumo ficam guardados.`}
            </span>
            <span className="flex gap-3">
              <Botao
                className="min-h-11"
                autoFocus
                disabled={removendo === "indo"}
                onClick={() => setRemovendo(null)}
              >
                Cancelar
              </Botao>
              <Botao
                tom="perigo"
                className="min-h-11"
                icone="act-delete"
                ocupado={removendo === "indo"}
                onClick={remove}
              >
                Remover
              </Botao>
            </span>
          </div>
        ) : saindo ? (
          <div
            role="alertdialog"
            aria-label="Mudanças não salvas"
            className="flex w-full flex-wrap items-center justify-between gap-3"
          >
            <span className="text-sm text-atencao">Há mudanças não salvas. Fechar descarta.</span>
            <span className="flex gap-3">
              <Botao className="min-h-11" autoFocus onClick={() => setSaindo(false)}>
                Continuar editando
              </Botao>
              <Botao tom="perigo" className="min-h-11" onClick={aoFechar}>
                Descartar e fechar
              </Botao>
            </span>
          </div>
        ) : (
          <div className="flex w-full flex-wrap items-center justify-between gap-3">
            <span className="flex min-w-0 items-center gap-3">
              {/* A zona de perigo é esta lixeira: o aviso dela cabe na pergunta, e não precisava de
                  um quadro vermelho dentro do popup para ser lido. */}
              <BotaoIcone
                icone="act-delete"
                rotulo="Remover o agente"
                explica="Ele para de atender. As conversas ficam guardadas."
                alinha="inicio"
                onClick={() => setRemovendo("perguntando")}
              />
              <span
                role="status"
                className={`min-w-0 text-sm ${
                  erroAoSalvar ? "text-perigo" : sujo ? "text-muted" : "text-ok"
                }`}
              >
                {erroAoSalvar || (sujo ? "Mudanças não salvas" : feito)}
              </span>
            </span>
            <span className="flex gap-3">
              {sujo && (
                <Botao className="min-h-11" disabled={salvando} onClick={descarta}>
                  Descartar
                </Botao>
              )}
              <Botao
                tom="solido"
                className="min-h-11"
                ocupado={salvando}
                disabled={!sujo}
                onClick={salvaTudo}
              >
                Salvar
              </Botao>
            </span>
          </div>
        )
      }
    >
      {erro ? (
        <div>
          <Aviso tom="erro" titulo="a ficha não abriu">
            {erro}
          </Aviso>
          <div className="mt-4">
            <Botao className="min-h-11" onClick={() => setTentativa((t) => t + 1)}>
              Tentar de novo
            </Botao>
          </div>
        </div>
      ) : !agente ? (
        <Carregando tipo="anel" o_que="abrindo a ficha" />
      ) : (
        <div className="flex min-h-0 flex-1 flex-col">
          {visitadas.map((a) => {
            const borda: Borda = { aba: a, aoSujar, registra };
            return (
              <div
                key={`${a}-${versao}`}
                id={`painel-${a}`}
                role="tabpanel"
                aria-labelledby={`aba-${a}`}
                hidden={aba !== a}
                className={aba !== a ? "" : "shrink-0"}
              >
                {a === "perfil" && (
                  <Perfil agente={agente} atualiza={atualiza} borda={borda} />
                )}
                {a === "canais" && <Canal agente={agente} atualiza={atualiza} />}
                {a === "comunicacao" && (
                  <Comunicacao agente={agente} atualiza={atualiza} borda={borda} />
                )}
                {a === "trabalho" && <Trabalho agente={agente} atualiza={atualiza} borda={borda} />}
                {a === "treinamento" && <Treinamento agente={agente} />}
                {a === "ferramentas" && (
                  <Ferramentas agente={agente} atualiza={atualiza} borda={borda} />
                )}
                {a === "configuracoes" && (
                  <Configuracoes agente={agente} atualiza={atualiza} borda={borda} />
                )}
              </div>
            );
          })}
        </div>
      )}
    </Modal>
  );
}

/** O que a aba conta à ficha: se tem mudança pendente, e como salvá-la. */
type Borda = {
  aba: Aba;
  aoSujar: (aba: Aba, sujo: boolean) => void;
  registra: (aba: Aba, salva: (() => Promise<string>) | null) => void;
};

/** Liga a aba ao salvar único da ficha. `salva` devolve o que foi salvo, em palavras, e levanta
 *  o erro: quem mostra os dois é o rodapé do popup. */
function usePendencia(borda: Borda, sujo: boolean, salva: () => Promise<string>) {
  const { aba, aoSujar, registra } = borda;
  useEffect(() => {
    aoSujar(aba, sujo);
  }, [aba, sujo, aoSujar]);
  // Sem lista de dependências: a função fecha sobre o estado deste desenho.
  useEffect(() => {
    registra(aba, salva);
  });
  useEffect(
    () => () => {
      aoSujar(aba, false);
      registra(aba, null);
    },
    [aba, aoSujar, registra],
  );
}

/** O salvar das abas que editam o agente: manda só o que mudou e conta o que foi. */
function useSalvar(
  agente: Agente,
  atualiza: (a: Agente) => void,
  mudancas: Partial<EdicaoDoAgente>,
  borda: Borda,
) {
  // Vazio no banco é `null` e na tela é `undefined`: os dois são o mesmo nada.
  const sujas = Object.entries(mudancas).filter(
    ([campo, valor]) =>
      JSON.stringify(valor ?? null) !==
      JSON.stringify((agente as unknown as Record<string, unknown>)[campo] ?? null),
  );

  usePendencia(borda, sujas.length > 0, async () => {
    atualiza(await api.editaAgente(agente.id, Object.fromEntries(sujas)));
    return sujas.map(([campo]) => NOME_DO_CAMPO[campo as keyof EdicaoDoAgente]).join(", ");
  });
}

function Perfil({
  agente,
  atualiza,
  borda,
}: {
  agente: Agente;
  atualiza: (a: Agente) => void;
  borda: Borda;
}) {
  const [nome, setNome] = useState(agente.nome);
  const [funcao, setFuncao] = useState(agente.perfil?.funcao ?? "");
  const [tom, setTom] = useState<TomDeVoz>(agente.tom);
  const [prompt, setPrompt] = useState<Prompt | null>(null);
  const [comportamento, setComportamento] = useState("");
  const [erroDaFoto, setErroDaFoto] = useState("");
  useEffect(() => {
    api
      .prompt(agente.id)
      .then((p) => {
        setPrompt(p);
        setComportamento(p.texto);
      })
      .catch(() => setPrompt(null));
  }, [agente.id]);

  // Três chamadas diferentes, um salvar só: o PATCH do nome e do tom, o perfil (que reescreve o
  // prompt) e o prompt à mão, nesta ordem, para o que o operador escreveu ficar por cima.
  const funcaoMudou = funcao !== (agente.perfil?.funcao ?? "");
  const comportamentoMudou = prompt !== null && comportamento !== prompt.texto;
  usePendencia(
    borda,
    funcaoMudou || comportamentoMudou || nome !== agente.nome || tom !== agente.tom,
    async () => {
      const salvas: string[] = [];
      const campos: Partial<EdicaoDoAgente> = {};
      if (nome !== agente.nome) campos.nome = nome;
      if (tom !== agente.tom) campos.tom = tom;
      if (Object.keys(campos).length > 0) {
        atualiza(await api.editaAgente(agente.id, campos));
        salvas.push(campos.nome ? "o nome" : "", campos.tom ? "o tom" : "");
      }
      if (funcaoMudou) {
        const resposta = await api.gravaPerfil(agente.id, {
          funcao: (funcao || null) as "suporte" | "vendas" | "atendimento" | null,
        });
        atualiza(resposta.agente);
        if (!comportamentoMudou) setComportamento(resposta.prompt);
        setPrompt((p) => (p ? { ...p, texto: resposta.prompt, gerado: resposta.prompt } : p));
        salvas.push("o que ele faz");
      }
      if (comportamentoMudou) {
        const resposta = await api.gravaPrompt(agente.id, comportamento);
        setPrompt((p) => (p ? { ...p, texto: resposta.texto } : p));
        salvas.push("o comportamento");
      }
      return salvas.filter(Boolean).join(", ");
    },
  );

  async function trocaFoto(arquivo: File) {
    setErroDaFoto("");
    try {
      atualiza(await api.mandaFoto(agente.id, arquivo));
    } catch (problema) {
      setErroDaFoto(problema instanceof ErroDaApi ? problema.message : String(problema));
    }
  }

  return (
    <section>
      {/* Quem ele é: a cara, o nome e o que ele faz. A situação se troca na lista. */}
      <div className="flex flex-wrap items-start gap-5">
        <Foto
          agente={agente}
          aoEnviar={trocaFoto}
          aoApagar={async () => atualiza(await api.removeFoto(agente.id))}
        />
        {erroDaFoto && (
          <p role="alert" className="text-sm text-perigo">
            {erroDaFoto}
          </p>
        )}
        <div className="min-w-[14rem] flex-1">
          <Campo rotulo="Nome" value={nome} onChange={(e) => setNome(e.target.value)} />
          <div className="mt-4">
            <p className="rotulo">O que ele faz</p>
            <div className="mt-2 flex flex-wrap gap-2">
              {FUNCOES.map((f) => (
                <button
                  key={f.valor}
                  onClick={() => setFuncao(f.valor)}
                  aria-pressed={funcao === f.valor}
                  className={`min-h-11 rounded-md border px-4 text-sm transition-colors ${
                    funcao === f.valor
                      ? "border-ciano text-ciano"
                      : "border-borda text-muted hover:text-texto"
                  }`}
                >
                  {f.rotulo}
                </button>
              ))}
            </div>
          </div>
        </div>
      </div>

      <div className="mt-8">
        <p className="rotulo">Como ele fala</p>
        <div className="mt-2 grid gap-2 sm:grid-cols-3">
          {TONS.map((t) => (
            <button
              key={t.valor}
              onClick={() => setTom(t.valor)}
              aria-pressed={tom === t.valor}
              className={`rounded-md border px-3 py-2 text-left transition-colors ${
                tom === t.valor ? "border-ciano bg-ciano/5" : "border-borda hover:border-dim"
              }`}
            >
              <span
                className={`block text-sm font-semibold ${tom === t.valor ? "text-ciano" : "text-texto"}`}
              >
                {t.rotulo}
              </span>
              <span className="mt-0.5 block text-xs text-muted">{t.explica}</span>
            </button>
          ))}
        </div>
      </div>

      {/* O prompt, no lugar onde se descreve o agente. Ele vinha escondido atrás de um "ver o que
          o agente vai ler", no fim da aba Trabalho. */}
      <div className="mt-8">
        <label className="block">
          <span className="rotulo">Comportamento</span>
          <span className="mt-1 block text-sm text-muted">
            Como ele se comporta na conversa. O formulário de Trabalho reescreve este texto.
          </span>
          {prompt === null ? (
            <span className="mt-2 block">
              <Carregando tipo="pontos" o_que="lendo o comportamento" mudo />
            </span>
          ) : (
            <textarea
              rows={10}
              value={comportamento}
              maxLength={20000}
              onChange={(e) => setComportamento(e.target.value)}
              className="mt-2 w-full rounded-md border border-borda bg-void p-3 text-sm leading-relaxed text-texto transition-colors focus:border-ciano focus:outline-none focus:ring-1 focus:ring-ciano"
            />
          )}
        </label>
      </div>

    </section>
  );
}

function Comunicacao({
  agente,
  atualiza,
  borda,
}: {
  agente: Agente;
  atualiza: (a: Agente) => void;
  borda: Borda;
}) {
  const [emojis, setEmojis] = useState<Emoji>(agente.emojis as Emoji);
  const [humano, setHumano] = useState(agente.transfere_para_humano);
  const [soDaEmpresa, setSoDaEmpresa] = useState(agente.restringe_temas);
  const [memoria, setMemoria] = useState(agente.memoria_ativa);
  const [avisaIa, setAvisaIa] = useState(agente.avisa_que_e_ia);
  const [partes, setPartes] = useState(agente.max_mensagens_por_resposta);
  const [buffer, setBuffer] = useState(agente.buffer_segundos);
  const [velocidade, setVelocidade] = useState(agente.digitacao_caracteres_por_segundo);
  const [teto, setTeto] = useState(agente.digitacao_maximo_segundos);
  const [ritmo, setRitmo] = useState(agente.ritmo);
  const comuns = {
    emojis,
    transfere_para_humano: humano,
    restringe_temas: soDaEmpresa,
    memoria_ativa: memoria,
    avisa_que_e_ia: avisaIa,
    max_mensagens_por_resposta: partes,
  };
  useSalvar(
    agente,
    atualiza,
    // Preset escreve os três números no servidor; à mão, manda os números e o ritmo vira
    // `manual` lá, pelo mesmo caminho do terminal.
    ritmo === "manual"
      ? {
          ...comuns,
          buffer_segundos: buffer,
          digitacao_caracteres_por_segundo: velocidade,
          digitacao_maximo_segundos: teto,
        }
      : { ...comuns, ritmo },
    borda,
  );

  return (
    <section>
      {/* Duas escolhas pequenas, lado a lado: a faixa do emoji sozinha na largura do popup
          parecia o campo mais importante da aba, e é o menos. */}
      <div className="mt-8 grid gap-6 sm:grid-cols-2">
        <Faixa
          rotulo="Emoji"
          opcoes={agente.emojis === "livre" ? EMOJIS_COM_LIVRE : EMOJIS}
          valor={emojis}
          aoMudar={(nivel) => setEmojis(nivel)}
          ajuda={
            // Agente anterior à escolha fica com a posição que ele tem hoje, "Como quiser", para
            // salvar outro campo desta aba não mudar o emoji dele sem ninguém pedir.
            agente.emojis === "livre"
              ? "Criado antes desta escolha, ele usa emoji como quiser. O que você escolher vale na próxima resposta."
              : undefined
          }
        />
        <Numero
          rotulo="Dividir a resposta em até"
          valor={partes}
          min={1}
          max={10}
          unidade="mensagens"
          aoMudar={setPartes}
        />
      </div>

      <p className="rotulo mt-8">Ritmo</p>
      <div className="mt-2 grid gap-2 sm:grid-cols-3">
        {RITMOS.map((r) => (
          <button
            key={r.valor}
            onClick={() => {
              setRitmo(r.valor);
              // O preset escreve os três números no servidor; a tela mostra os de agora até salvar.
              const [espera, velocidadeNova, tetoNovo] = NUMEROS_DO_RITMO[r.valor];
              setBuffer(espera);
              setVelocidade(velocidadeNova);
              setTeto(tetoNovo);
            }}
            aria-pressed={ritmo === r.valor}
            className={`rounded-md border px-3 py-2 text-left transition-colors ${
              ritmo === r.valor ? "border-ciano bg-ciano/5" : "border-borda hover:border-dim"
            }`}
          >
            <span
              className={`block text-sm font-semibold ${ritmo === r.valor ? "text-ciano" : "text-texto"}`}
            >
              {r.rotulo}
            </span>
            <span className="mt-0.5 block text-xs text-muted">{r.explica}</span>
          </button>
        ))}
      </div>
      {/* Os três números do ritmo ficam à vista, com o que o preset escolheu: escondê-los atrás de
          um "ajustar à mão" fazia o operador clicar só para saber o que estava valendo. Mexer num
          deles é o que torna o ritmo manual. */}
      <div className="mt-6 grid gap-6 sm:grid-cols-2">
            <Numero
              rotulo="Esperar antes de responder"
              valor={buffer}
              min={1}
              max={60}
              unidade="segundos"
              aoMudar={(v) => {
                setBuffer(v);
                setRitmo("manual");
              }}
              ajuda="Tempo para a pessoa terminar de escrever."
            />
            <Numero
              rotulo="Velocidade de digitação"
              valor={velocidade}
              min={1}
              max={30}
              unidade="caracteres por segundo"
              aoMudar={(v) => {
                setVelocidade(v);
                setRitmo("manual");
              }}
            />
            <Numero
              rotulo="Mostrar digitando por no máximo"
              valor={teto}
              min={1}
              max={30}
              unidade="segundos por mensagem"
              aoMudar={(v) => {
                setTeto(v);
                setRitmo("manual");
              }}
            />
      </div>

      <div className="mt-8 flex flex-col border-t border-borda pt-6">
        <Interruptor
          ligado={humano}
          aoMudar={setHumano}
          rotulo="Passar a conversa para uma pessoa"
          descricao="Desligado, ele nunca promete atendimento humano e atende até o fim sozinho."
        />
        <Interruptor
          ligado={soDaEmpresa}
          aoMudar={setSoDaEmpresa}
          rotulo="Falar só de assuntos da empresa"
          descricao="Puxou outro assunto, ele volta ao atendimento em uma frase."
        />
        <Interruptor
          ligado={memoria}
          aoMudar={setMemoria}
          rotulo="Lembrar de cada contato"
          descricao="Ele guarda o que ficou combinado e não pergunta duas vezes. Em Contatos você vê e apaga."
        />
        <Interruptor
          ligado={avisaIa}
          aoMudar={setAvisaIa}
          rotulo="Avisar que é um assistente virtual"
          descricao="Uma linha na primeira mensagem de cada conversa. Quem atende na União Europeia precisa ligar."
        />
      </div>

    </section>
  );
}

function Trabalho({
  agente,
  atualiza,
  borda,
}: {
  agente: Agente;
  atualiza: (a: Agente) => void;
  borda: Borda;
}) {
  const [prompt, setPrompt] = useState<Prompt | null>(null);
  const [publico, setPublico] = useState(agente.perfil?.publico ?? "");
  const [site, setSite] = useState(agente.perfil?.site ?? "");
  const [sobre, setSobre] = useState(agente.perfil?.sobre_empresa ?? "");
  const [nuncaDizer, setNuncaDizer] = useState(agente.perfil?.nunca_dizer ?? "");
  const [assina, setAssina] = useState(agente.assina_nome);

  const formularioMudou =
    publico !== (agente.perfil?.publico ?? "") ||
    site !== (agente.perfil?.site ?? "") ||
    sobre !== (agente.perfil?.sobre_empresa ?? "") ||
    nuncaDizer !== (agente.perfil?.nunca_dizer ?? "") ||
    assina !== agente.assina_nome;
  // O comportamento do Perfil é este mesmo texto: salvar aqui o reescreve, e o aviso abaixo diz
  // isso antes, quando o operador já mexeu nele à mão.
  const editadoAMao = prompt !== null && prompt.texto !== prompt.gerado;

  usePendencia(borda, formularioMudou, async () => {
    const salvas: string[] = [];
    if (formularioMudou) {
      const resposta = await api.gravaPerfil(agente.id, {
        publico: publico || null,
        site: site || null,
        sobre_empresa: sobre || null,
        nunca_dizer: nuncaDizer || null,
        assina_nome: assina,
      });
      atualiza(resposta.agente);
      setPrompt((p) => (p ? { ...p, texto: resposta.prompt, gerado: resposta.prompt } : p));
      salvas.push("o trabalho dele, com o comportamento reescrito");
    }
    return salvas.join(", ");
  });

  // Só para saber se o comportamento foi escrito à mão, e avisar antes de reescrevê-lo.
  useEffect(() => {
    api
      .prompt(agente.id)
      .then(setPrompt)
      .catch(() => setPrompt(null));
  }, [agente.id]);

  return (
    <section>
      <p className="max-w-[70ch] text-sm text-muted">
        O que você responde aqui vira o prompt do agente.
      </p>

      <div className="mt-6 grid gap-6 sm:grid-cols-2">
        <Campo
          rotulo="Quem fala com ele"
          value={publico}
          onChange={(e) => setPublico(e.target.value)}
          placeholder="quem procura tênis de corrida"
        />
        <Campo
          rotulo="Site"
          value={site}
          onChange={(e) => setSite(e.target.value)}
          placeholder="https://"
        />
      </div>

      <label className="mt-6 block">
        <span className="rotulo">Sobre {agente.empresa}</span>
        <textarea
          rows={5}
          value={sobre}
          onChange={(e) => setSobre(e.target.value)}
          className="mt-2 w-full rounded-md border border-borda bg-surface px-3 py-2 text-sm text-texto transition-colors placeholder:text-dim focus:border-ciano focus:outline-none focus:ring-1 focus:ring-ciano"
        />
      </label>

      <label className="mt-6 block">
        <span className="rotulo">O que ele nunca deve dizer</span>
        <span className="mt-1 block text-sm text-muted">
          Uma regra por linha. É o jeito mais direto de cortar a promessa que a empresa não cumpre.
        </span>
        <textarea
          rows={3}
          value={nuncaDizer}
          onChange={(e) => setNuncaDizer(e.target.value)}
          placeholder={"entregamos em 24 horas\nque somos os mais baratos"}
          className="mt-2 w-full rounded-md border border-borda bg-surface px-3 py-2 text-sm text-texto transition-colors placeholder:text-dim focus:border-ciano focus:outline-none focus:ring-1 focus:ring-ciano"
        />
      </label>

      <div className="mt-4">
        <Interruptor
          ligado={assina}
          aoMudar={setAssina}
          rotulo="Assinar o nome do agente"
          descricao="Ele acrescenta o próprio nome no fim da resposta."
        />
      </div>

      {/* Sem botão aqui: o Salvar é o do rodapé. O aviso fica, porque é ele que impede a perda. */}
      {editadoAMao && formularioMudou && (
        <div className="mt-6">
          <Aviso tom="atencao" titulo="salvar reescreve o comportamento">
            Ele foi escrito à mão, em Perfil, e essa edição se perde. Para manter, descarte as
            mudanças desta aba.
          </Aviso>
        </div>
      )}

    </section>
  );
}

function Ferramentas({
  agente,
  atualiza,
  borda,
}: {
  agente: Agente;
  atualiza: (a: Agente) => void;
  borda: Borda;
}) {
  const [catalogo, setCatalogo] = useState<Ferramenta[] | null>(null);
  const [ligadas, setLigadas] = useState<string[]>(agente.ferramentas);
  const [horas, setHoras] = useState(agente.retomada_automatica_horas ?? 0);
  useSalvar(
    agente,
    atualiza,
    { ferramentas: ligadas, retomada_automatica_horas: horas === 0 ? null : horas },
    borda,
  );

  useEffect(() => {
    api.ferramentas().then(setCatalogo).catch(() => setCatalogo([]));
  }, []);

  return (
    <section>
      {/* Um cartão por ferramenta: ícone, nome e pronto. A descrição de cada uma ocupava três
          linhas e o operador já sabe o que uma calculadora faz; o que ele precisa ver de relance é
          o que está ligado. */}
      {catalogo === null ? (
        <Carregando tipo="pontos" o_que="buscando o catálogo" />
      ) : (
        <div className="grid gap-3 sm:grid-cols-2 lg:grid-cols-3">
          {catalogo.map((f) => {
            const ligada = ligadas.includes(f.nome);
            return (
              <button
                key={f.nome}
                onClick={() =>
                  setLigadas(ligada ? ligadas.filter((n) => n !== f.nome) : [...ligadas, f.nome])
                }
                role="switch"
                aria-checked={ligada}
                title={f.descricao}
                className={`flex min-h-11 items-center gap-3 rounded-lg border p-4 text-left transition-colors ${
                  ligada
                    ? "border-ok/40 bg-ok/5 text-texto"
                    : "border-borda text-muted hover:border-dim hover:text-texto"
                }`}
              >
                <Icone
                  nome={ICONE_DA_FERRAMENTA[f.nome] ?? "nav-settings"}
                  tamanho={20}
                  className={ligada ? "text-ok" : "text-dim"}
                />
                <span className="min-w-0 flex-1 truncate text-sm font-medium">{f.rotulo}</span>
                {ligada && <Icone nome="act-check" tamanho={16} className="shrink-0 text-ok" />}
              </button>
            );
          })}
        </div>
      )}

      {/* Passar para uma pessoa se liga e desliga em Comunicação, e só lá: aqui havia um
          interruptor travado em "sempre ligada" que dizia o contrário. */}
      {/* Prazo é escolha, não régua: ninguém arrasta até 37 horas. As opções são as que o
          operador usa, e "sem prazo" é uma delas, não o zero da ponta esquerda. */}
      {agente.transfere_para_humano && (
        <label className="mt-8 block max-w-sm">
          <span className="rotulo">Depois de passar para uma pessoa, ele volta em</span>
          <select
            value={horas}
            onChange={(e) => setHoras(Number(e.target.value))}
            className="mt-2 min-h-11 w-full rounded-md border border-borda bg-surface px-3 text-sm text-texto transition-colors focus:border-ciano focus:outline-none"
          >
            {PRAZOS.map((p) => (
              <option key={p.horas} value={p.horas}>
                {p.rotulo}
              </option>
            ))}
          </select>
        </label>
      )}

      <div className="mt-8 rounded-lg border border-borda p-5 opacity-60">
        <div className="flex items-center justify-between gap-4">
          <p className="text-sm text-texto">Google Agenda</p>
          <Selo>em breve</Selo>
        </div>
        <p className="mt-1 text-sm text-muted">
          Marcar, remarcar e desmarcar compromisso direto na conversa.
        </p>
      </div>

    </section>
  );
}

/** As quatro funções de IA que o escolhedor conhece. Função que a API trouxer fora desta lista
 *  cai no campo de texto, para uma função nova não travar a aba. */
/** As cores do painel que servem de fundo para a inicial, na mesma ordem do servidor
 *  (`agentes/avatar.py`). Nome de token, nunca hexadecimal. */
const CORES_DO_AVATAR: { valor: CorDeAvatar; rotulo: string; amostra: string }[] = [
  { valor: "ciano", rotulo: "Ciano", amostra: "bg-ciano" },
  { valor: "ok", rotulo: "Verde", amostra: "bg-ok" },
  { valor: "atencao", rotulo: "Âmbar", amostra: "bg-atencao" },
  { valor: "texto", rotulo: "Claro", amostra: "bg-texto" },
];

const FUNCOES_DE_IA = ["conversa", "auxiliar", "visao", "transcricao"] as const;
type FuncaoDeIA = (typeof FUNCOES_DE_IA)[number];
const eFuncaoDeIA = (f: string): f is FuncaoDeIA => (FUNCOES_DE_IA as readonly string[]).includes(f);

/** Os modelos do agente e quem ele atende.
 *
 *  Eram cinco campos de texto cru pedindo o formato `provedor:modelo`, enquanto o onboarding já
 *  tinha o escolhedor pronto ao lado (auditoria de copy de 2026-09-18). Agora cada função mostra o
 *  modelo de hoje e abre o mesmo `EscolheIA`, um de cada vez: cinco escolhedores abertos não
 *  caberiam na aba, e cada um busca a própria lista no provedor.
 */
function Configuracoes({
  agente,
  atualiza,
  borda,
}: {
  agente: Agente;
  atualiza: (a: Agente) => void;
  borda: Borda;
}) {
  const [modelos, setModelos] = useState<Modelos | null>(null);
  const [valores, setValores] = useState<Record<string, string>>({
    modelo_conversa: agente.modelo_conversa,
    modelo_fallback: agente.modelo_fallback ?? "",
    modelo_auxiliar: agente.modelo_auxiliar,
    modelo_visao: agente.modelo_visao,
    modelo_transcricao: agente.modelo_transcricao,
  });
  const [contatos, setContatos] = useState(agente.contatos_permitidos.join(", "));
  const [cor, setCor] = useState(agente.avatar_cor);
  const [trocando, setTrocando] = useState("");

  const mudancas: Partial<EdicaoDoAgente> = {
    avatar_cor: cor,
    modelo_fallback: valores.modelo_fallback || null,
    contatos_permitidos: contatos
      .split(",")
      .map((c) => c.trim())
      .filter(Boolean),
  };
  // Trocar de provedor esvazia o modelo enquanto a lista não chega: função obrigatória vazia não
  // vai para o banco, senão um clique no meio do caminho volta como erro de validação.
  if (valores.modelo_conversa) mudancas.modelo_conversa = valores.modelo_conversa;
  if (valores.modelo_auxiliar) mudancas.modelo_auxiliar = valores.modelo_auxiliar;
  if (valores.modelo_visao) mudancas.modelo_visao = valores.modelo_visao;
  if (valores.modelo_transcricao) mudancas.modelo_transcricao = valores.modelo_transcricao;
  useSalvar(
    agente,
    atualiza,
    mudancas,
    borda,
  );

  useEffect(() => {
    api.modelos().then(setModelos).catch(() => setModelos(null));
  }, []);

  return (
    <section>
      {modelos === null ? (
        <Carregando tipo="pontos" o_que="buscando os modelos" />
      ) : (
        <div className="flex flex-col divide-y divide-borda rounded-lg border border-borda">
          {modelos.funcoes.map((f) => {
            const aberto = trocando === f.campo;
            const escolhido = valores[f.campo] ?? "";
            return (
              <div key={f.campo} className="p-4">
                <div className="flex flex-wrap items-center justify-between gap-3">
                  <div className="min-w-0">
                    <p className="text-sm text-texto">{f.rotulo}</p>
                    <p className={`tecnico mt-1 break-all ${escolhido ? "text-muted" : "text-dim"}`}>
                      {escolhido || (f.obrigatorio ? "escolha um modelo" : "sem reserva")}
                    </p>
                  </div>
                  <Botao
                    className="min-h-11"
                    aria-expanded={aberto}
                    aria-label={`${aberto ? "Fechar" : "Trocar"}: ${f.rotulo}`}
                    onClick={() => setTrocando(aberto ? "" : f.campo)}
                  >
                    {aberto ? "Fechar" : "Trocar"}
                  </Botao>
                </div>

                {aberto && (
                  <div className="mt-4">
                    {eFuncaoDeIA(f.funcao) ? (
                      <EscolheIA
                        funcao={f.funcao}
                        valor={escolhido}
                        aoMudar={(m) => setValores((v) => ({ ...v, [f.campo]: m }))}
                      />
                    ) : (
                      <Campo
                        rotulo="Modelo"
                        value={escolhido}
                        placeholder={modelos.padroes[f.campo] ?? undefined}
                        onChange={(e) => setValores((v) => ({ ...v, [f.campo]: e.target.value }))}
                      />
                    )}
                    {!f.obrigatorio && escolhido && (
                      <div className="mt-4">
                        <Botao
                          pequeno
                          icone="act-delete"
                          onClick={() => {
                            setValores((v) => ({ ...v, [f.campo]: "" }));
                            setTrocando("");
                          }}
                        >
                          Remover a reserva
                        </Botao>
                      </div>
                    )}
                  </div>
                )}
              </div>
            );
          })}
        </div>
      )}

      {!agente.avatar && (
        <div className="mt-8">
          <p className="rotulo">Cor da inicial</p>
          <p className="mt-1 text-sm text-muted">
            O fundo da letra na lista, enquanto o agente não tiver foto.
          </p>
          <div className="mt-2 flex gap-2" role="group" aria-label="Cor da inicial">
            {CORES_DO_AVATAR.map((c) => (
              <button
                key={c.valor}
                onClick={() => setCor(c.valor)}
                aria-label={c.rotulo}
                aria-pressed={cor === c.valor}
                title={c.rotulo}
                className={`h-8 w-8 rounded-full border-2 transition-colors ${c.amostra} ${
                  cor === c.valor ? "border-texto" : "border-transparent hover:border-dim"
                }`}
              />
            ))}
          </div>
        </div>
      )}

      <div className="mt-8">
        <Campo
          rotulo="Telefones que ele atende"
          value={contatos}
          onChange={(e) => setContatos(e.target.value)}
          placeholder="5511999990000, 5511888880000"
          aria-describedby="ajuda-dos-telefones"
        />
        <p id="ajuda-dos-telefones" className="mt-2 text-sm text-dim">
          Separados por vírgula. Vazio, ele atende qualquer pessoa.
        </p>
      </div>
    </section>
  );
}

function Numero({
  rotulo,
  valor,
  min,
  max,
  unidade,
  ajuda,
  aoMudar,
}: {
  rotulo: string;
  valor: number;
  min: number;
  max: number;
  unidade: string;
  ajuda?: string;
  aoMudar: (v: number) => void;
}) {
  return (
    <label className="block">
      <span className="flex items-baseline justify-between gap-4">
        <span className="rotulo">{rotulo}</span>
        {/* Mono só no número: a unidade é palavra, e palavra é Inter (v0.21.0). */}
        <span className="text-right text-sm text-texto">
          {valor > 0 && <span className="font-mono">{valor} </span>}
          {unidade}
        </span>
      </span>
      <input
        type="range"
        min={min}
        max={max}
        value={valor}
        onChange={(e) => aoMudar(Number(e.target.value))}
        className="mt-3 w-full accent-ciano"
      />
      {ajuda && <span className="mt-1 block text-sm text-dim">{ajuda}</span>}
    </label>
  );
}
