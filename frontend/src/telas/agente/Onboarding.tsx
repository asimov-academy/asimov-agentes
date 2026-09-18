import { useCallback, useEffect, useMemo, useState } from "react";
import {
  api,
  ErroDaApi,
  type Agente,
  type CanalDisponivel,
  type Empresa,
  type Ferramenta,
  type NivelDeEmoji,
} from "../../api/cliente";
import { Aviso } from "../../design/Aviso";
import { Botao } from "../../design/Botao";
import { Campo } from "../../design/Campo";
import { Carregando } from "../../design/Carregando";
import { Icone } from "../../design/Icone";
import { Interruptor } from "../../design/Interruptor";
import { Modal } from "../../design/Modal";
import { Passos } from "../../design/Passos";
import { CANAIS } from "./canais";
import { EscolheIA } from "./EscolheIA";
import { Previa } from "./Previa";
import { Teste } from "./Teste";

/** O onboarding do agente, no popup grande com o fundo embaçado.
 *
 *  Oito passos na mesma ordem do terminal, um por vez, com a prévia viva ao lado. Só empresa, canal
 *  e nome travam; o resto tem padrão e dá para pular. A criação é uma chamada só no fim: passo
 *  nenhum grava pela metade, então desistir no meio não deixa agente capenga no banco.
 *
 *  O rascunho fica no navegador. Fechar o notebook e voltar não perde o que já foi respondido.
 */

const RASCUNHO = "asimov:onboarding";

const PASSOS = [
  "Empresa",
  "Canal",
  "Nome e função",
  "Sobre a empresa",
  "Jeito de falar",
  "Ferramentas",
  "IA",
  "Conferir",
];

const FUNCOES: { valor: string; rotulo: string; explica: string }[] = [
  { valor: "atendimento", rotulo: "Atendimento", explica: "Recebe quem chega, tira dúvidas e encaminha." },
  { valor: "suporte", rotulo: "Suporte", explica: "Resolve problema de quem já é cliente." },
  { valor: "vendas", rotulo: "Vendas", explica: "Ajuda quem está decidindo a comprar." },
];

const EMOJIS: { valor: NivelDeEmoji; rotulo: string }[] = [
  { valor: "nenhum", rotulo: "Nenhum" },
  { valor: "pouco", rotulo: "Pouco" },
  { valor: "medio", rotulo: "Médio" },
  { valor: "muito", rotulo: "Muito" },
];

type Rascunho = {
  empresaId: string;
  empresaNova: string;
  canal: string;
  nome: string;
  funcao: string;
  publico: string;
  site: string;
  sobre: string;
  emojis: NivelDeEmoji;
  partes: number;
  buffer: number;
  ferramentas: string[];
  modelo: string;
};

const VAZIO: Rascunho = {
  empresaId: "",
  empresaNova: "",
  canal: "",
  nome: "",
  funcao: "atendimento",
  publico: "",
  site: "",
  sobre: "",
  emojis: "nenhum",
  partes: 3,
  buffer: 8,
  ferramentas: [],
  modelo: "",
};

function leRascunho(): Rascunho {
  try {
    const guardado = localStorage.getItem(RASCUNHO);
    return guardado ? { ...VAZIO, ...JSON.parse(guardado) } : VAZIO;
  } catch {
    return VAZIO;
  }
}

export function Onboarding({
  empresas,
  aoFechar,
  aoCriar,
}: {
  empresas: Empresa[];
  aoFechar: () => void;
  aoCriar: (agente: Agente) => void;
}) {
  const [passo, setPasso] = useState(0);
  const [dados, setDados] = useState<Rascunho>(leRascunho);
  const [canais, setCanais] = useState<CanalDisponivel[]>([]);
  const [ferramentas, setFerramentas] = useState<Ferramenta[]>([]);
  const [erro, setErro] = useState("");
  const [salvando, setSalvando] = useState(false);
  const [listaDeEmpresas, setListaDeEmpresas] = useState(empresas);
  const [criado, setCriado] = useState<Agente | null>(null);

  useEffect(() => {
    Promise.all([api.canais(), api.ferramentas()])
      .then(([c, f]) => {
        setCanais(c);
        setFerramentas(f);
      })
      .catch((problema) => setErro(problema.message));
  }, []);

  // Uma empresa só: ela já vem escolhida, e o passo vira confirmação em vez de pergunta.
  useEffect(() => {
    if (!dados.empresaId && listaDeEmpresas.length === 1) {
      setDados((antes) => ({ ...antes, empresaId: listaDeEmpresas[0].id }));
    }
  }, [listaDeEmpresas, dados.empresaId]);

  useEffect(() => {
    try {
      localStorage.setItem(RASCUNHO, JSON.stringify(dados));
    } catch {
      // Navegador sem armazenamento: o onboarding continua, só sem rascunho.
    }
  }, [dados]);

  const muda = useCallback(
    <C extends keyof Rascunho>(campo: C, valor: Rascunho[C]) =>
      setDados((antes) => ({ ...antes, [campo]: valor })),
    [],
  );

  const empresaEscolhida = listaDeEmpresas.find((e) => e.id === dados.empresaId);

  const podeAvancar = useMemo(() => {
    if (passo === 0) return Boolean(dados.empresaId || dados.empresaNova.trim());
    if (passo === 1) return Boolean(dados.canal);
    if (passo === 2) return Boolean(dados.nome.trim());
    if (passo === 6) return dados.modelo.includes(":") && !dados.modelo.endsWith(":");
    return true;
  }, [passo, dados]);

  async function avanca() {
    setErro("");
    // A empresa nova nasce aqui, e não no fim: sem ela o agente não tem onde nascer.
    if (passo === 0 && !dados.empresaId && dados.empresaNova.trim()) {
      setSalvando(true);
      try {
        const criada = await api.criaEmpresa(dados.empresaNova.trim());
        setListaDeEmpresas((antes) => [...antes, criada]);
        muda("empresaId", criada.id);
      } catch (problema) {
        setErro(problema instanceof ErroDaApi ? problema.message : String(problema));
        return;
      } finally {
        setSalvando(false);
      }
    }
    setPasso((p) => Math.min(p + 1, PASSOS.length - 1));
  }

  async function cria() {
    setErro("");
    setSalvando(true);
    try {
      const agente = await api.criaAgente(dados.empresaId, {
        nome: dados.nome.trim(),
        canal: dados.canal,
        emojis: dados.emojis,
        max_mensagens_por_resposta: dados.partes,
        buffer_segundos: dados.buffer,
        ferramentas: dados.ferramentas,
        modelo_conversa: dados.modelo,
      });
      if (dados.funcao || dados.publico || dados.site || dados.sobre) {
        await api.gravaPerfil(agente.id, {
          funcao: dados.funcao as "suporte" | "vendas" | "atendimento",
          publico: dados.publico || null,
          site: dados.site || null,
          sobre_empresa: dados.sobre || null,
        });
      }
      localStorage.removeItem(RASCUNHO);
      setDados(VAZIO);
      setCriado(agente);
    } catch (problema) {
      setErro(problema instanceof ErroDaApi ? problema.message : String(problema));
    } finally {
      setSalvando(false);
    }
  }

  function sai() {
    const escreveu = dados.nome.trim() || dados.canal || dados.sobre.trim();
    if (escreveu && !window.confirm("Sair do onboarding? O rascunho fica guardado para depois.")) {
      return;
    }
    aoFechar();
  }

  // O fim não é um "pronto": é falar com o agente antes de sair da tela.
  if (criado) {
    return (
      <Modal
        titulo={`${criado.nome} está de pé`}
        subtitulo={`em ${criado.empresa}, ${CANAIS[criado.canal]?.rotulo ?? criado.canal}`}
        aoFechar={() => aoCriar(criado)}
        largura="max-w-3xl"
        rodape={
          <>
            <Botao pequeno onClick={() => aoCriar(criado)}>
              Ver a ficha
            </Botao>
            <Botao
              tom="solido"
              pequeno
              icone="act-add"
              onClick={() => {
                setCriado(null);
                setPasso(0);
              }}
            >
              Criar outro
            </Botao>
          </>
        }
      >
        <div className="mb-6 flex items-start gap-3 border-l-4 border-l-ok pl-4">
          <div>
            <p className="text-base text-texto">Fale com ele agora.</p>
            <p className="mt-1 max-w-[60ch] text-sm text-muted">
              {criado.canal === "nativo"
                ? "Ele ainda não atende ninguém de fora. Conecte a um canal pela ficha quando quiser."
                : `Ele nasceu sem conectar ao canal. Você conecta pela ficha quando tiver em mãos: ${CANAIS[criado.canal]?.exige.toLowerCase() ?? "o acesso do canal"}`}
            </p>
          </div>
        </div>

        <Teste
          agenteId={criado.id}
          agente={criado.nome}
          primeiraMensagem="Oi, tudo bem? Queria tirar uma dúvida."
        />
      </Modal>
    );
  }

  return (
    <Modal
      titulo="Novo agente"
      subtitulo={`Passo ${passo + 1} de ${PASSOS.length}: ${PASSOS[passo]}`}
      aoFechar={sai}
      rodape={
        <>
          {passo > 0 && (
            <Botao pequeno onClick={() => setPasso((p) => p - 1)}>
              Voltar
            </Botao>
          )}
          {passo < PASSOS.length - 1 ? (
            <Botao tom="solido" pequeno onClick={avanca} ocupado={salvando} disabled={!podeAvancar}>
              Continuar
            </Botao>
          ) : (
            <Botao tom="acento" pequeno icone="act-save" onClick={cria} ocupado={salvando}>
              Criar agente
            </Botao>
          )}
        </>
      }
    >
      <div className="grid gap-8 lg:grid-cols-[10rem_1fr_18rem]">
        <Passos passos={PASSOS} atual={passo} aoIr={(i) => setPasso(i)} />

        <div className="min-w-0">
          {erro && (
            <div className="mb-6">
              <Aviso tom="erro" titulo="não deu para continuar">
                {erro}
              </Aviso>
            </div>
          )}

          {passo === 0 && (
            <Pergunta
              titulo="De qual empresa é este agente?"
              ajuda="Cada empresa tem os próprios agentes, conversas e prompts, separados das outras."
            >
              {listaDeEmpresas.length > 0 && (
                <div className="flex flex-col gap-2">
                  {listaDeEmpresas.map((e) => (
                    <Escolha
                      key={e.id}
                      marcada={dados.empresaId === e.id}
                      aoMarcar={() => {
                        muda("empresaId", e.id);
                        muda("empresaNova", "");
                      }}
                    >
                      {e.nome}
                    </Escolha>
                  ))}
                </div>
              )}
              <div className="mt-6 border-t border-borda pt-6">
                <Campo
                  rotulo="Ou crie uma empresa"
                  placeholder="Nome da empresa"
                  value={dados.empresaNova}
                  onChange={(e) => {
                    muda("empresaNova", e.target.value);
                    if (e.target.value) muda("empresaId", "");
                  }}
                />
              </div>
            </Pergunta>
          )}

          {passo === 1 && (
            <Pergunta
              titulo="Por onde ele vai atender?"
              ajuda="Cada cartão diz o que você precisa ter na mão antes de começar."
            >
              {canais.length === 0 ? (
                <Carregando tipo="pontos" o_que="buscando os canais" />
              ) : (
                <div className="grid gap-3 sm:grid-cols-2">
                  {canais.map((c) => {
                    const texto = CANAIS[c.nome];
                    const marcado = dados.canal === c.nome;
                    return (
                      <button
                        key={c.nome}
                        onClick={() => muda("canal", c.nome)}
                        className={`relative flex flex-col gap-2 border p-4 text-left transition-colors ${
                          marcado ? "border-ciano bg-ciano/5" : "border-borda hover:border-dim"
                        }`}
                      >
                        <span className="flex items-center gap-2">
                          <Icone nome={texto?.icone ?? "cont-link"} className={marcado ? "text-ciano" : "text-muted"} />
                          <span className="text-sm font-semibold text-texto">
                            {texto?.rotulo ?? c.nome}
                          </span>
                        </span>
                        <span className="text-sm leading-snug text-muted">{texto?.serve}</span>
                        <span className="mt-1 text-xs leading-snug text-dim">
                          Você vai precisar de: {texto?.exige ?? "nada"}
                        </span>
                      </button>
                    );
                  })}
                </div>
              )}
            </Pergunta>
          )}

          {passo === 2 && (
            <Pergunta
              titulo="Como ele se chama, e o que ele faz?"
              ajuda="O nome aparece para quem conversa com ele."
            >
              <Campo
                rotulo="Nome do agente"
                placeholder="Ana"
                value={dados.nome}
                onChange={(e) => muda("nome", e.target.value)}
                autoFocus
              />
              <div className="mt-6 flex flex-col gap-2">
                {FUNCOES.map((f) => (
                  <Escolha
                    key={f.valor}
                    marcada={dados.funcao === f.valor}
                    aoMarcar={() => muda("funcao", f.valor)}
                    explica={f.explica}
                  >
                    {f.rotulo}
                  </Escolha>
                ))}
              </div>
            </Pergunta>
          )}

          {passo === 3 && (
            <Pergunta
              titulo={`O que o agente precisa saber sobre ${empresaEscolhida?.nome ?? "a empresa"}?`}
              ajuda="Isto vira o prompt dele. Pode pular e escrever depois, na aba Trabalho."
            >
              <Campo
                rotulo="Quem fala com ele"
                placeholder="quem procura tênis de corrida"
                value={dados.publico}
                onChange={(e) => muda("publico", e.target.value)}
              />
              <div className="mt-4">
                <Campo
                  rotulo="Site (opcional)"
                  placeholder="https://"
                  value={dados.site}
                  onChange={(e) => muda("site", e.target.value)}
                />
              </div>
              <label className="mt-6 block">
                <span className="rotulo">Sobre a empresa</span>
                <textarea
                  rows={5}
                  value={dados.sobre}
                  onChange={(e) => muda("sobre", e.target.value)}
                  placeholder="O que ela vende, desde quando, o que a diferencia."
                  className="mt-2 w-full border-b border-dim bg-surface px-3 py-2 text-sm text-texto transition-colors placeholder:text-dim focus:border-ciano focus:outline-none"
                />
              </label>
            </Pergunta>
          )}

          {passo === 4 && (
            <Pergunta
              titulo="Como ele fala?"
              ajuda="A prévia ao lado muda junto: escolha e veja o efeito."
            >
              <p className="rotulo">Emoji</p>
              <div className="mt-2 flex flex-wrap gap-2">
                {EMOJIS.map((e) => (
                  <button
                    key={e.valor}
                    onClick={() => muda("emojis", e.valor)}
                    className={`border px-4 py-2 text-sm transition-colors ${
                      dados.emojis === e.valor
                        ? "border-ciano text-ciano"
                        : "border-borda text-muted hover:text-texto"
                    }`}
                  >
                    {e.rotulo}
                  </button>
                ))}
              </div>

              <div className="mt-6">
                <Deslizante
                  rotulo="Dividir a resposta em até"
                  valor={dados.partes}
                  min={1}
                  max={5}
                  unidade={dados.partes === 1 ? "mensagem" : "mensagens"}
                  aoMudar={(v) => muda("partes", v)}
                />
              </div>
              <div className="mt-6">
                <Deslizante
                  rotulo="Esperar antes de responder"
                  valor={dados.buffer}
                  min={1}
                  max={30}
                  unidade="segundos"
                  aoMudar={(v) => muda("buffer", v)}
                  ajuda="Tempo para a pessoa terminar de escrever antes de o agente responder."
                />
              </div>
            </Pergunta>
          )}

          {passo === 5 && (
            <Pergunta
              titulo="O que ele pode usar?"
              ajuda="Ferramenta ligada gasta token em todo turno. O agente nasce sem nenhuma."
            >
              {ferramentas.length === 0 ? (
                <Carregando tipo="pontos" o_que="buscando o catálogo" />
              ) : (
                <div className="flex flex-col gap-1">
                  {ferramentas.map((f) => (
                    <Interruptor
                      key={f.nome}
                      ligado={dados.ferramentas.includes(f.nome)}
                      aoMudar={(ligado) =>
                        muda(
                          "ferramentas",
                          ligado
                            ? [...dados.ferramentas, f.nome]
                            : dados.ferramentas.filter((n) => n !== f.nome),
                        )
                      }
                      rotulo={f.rotulo}
                      descricao={f.descricao}
                    />
                  ))}
                </div>
              )}
              <p className="mt-6 text-sm text-dim">
                Passar a conversa para uma pessoa está sempre ligado.
              </p>
            </Pergunta>
          )}

          {passo === 6 && (
            <Pergunta
              titulo="Qual IA responde por ele?"
              ajuda="Cada agente tem a própria. Resumo, imagem e áudio nascem no mesmo provedor e mudam depois, na ficha."
            >
              <EscolheIA funcao="conversa" valor={dados.modelo} aoMudar={(m) => muda("modelo", m)} />
              <p className="mt-6 text-sm text-dim">
                A Anthropic não transcreve áudio: com ela, guarde também a chave da OpenAI, da Groq ou
                do Gemini para o agente ouvir áudio.
              </p>
            </Pergunta>
          )}

          {passo === 7 && (
            <Pergunta
              titulo="Confere e cria"
              ajuda="Nada foi gravado ainda. O agente nasce inteiro quando você clicar."
            >
              <dl className="flex flex-col divide-y divide-borda border-y border-borda">
                <Linha rotulo="Empresa">{empresaEscolhida?.nome ?? dados.empresaNova}</Linha>
                <Linha rotulo="Canal">{CANAIS[dados.canal]?.rotulo ?? dados.canal}</Linha>
                <Linha rotulo="Nome">{dados.nome}</Linha>
                <Linha rotulo="Função">
                  {FUNCOES.find((f) => f.valor === dados.funcao)?.rotulo ?? "sem função"}
                </Linha>
                <Linha rotulo="IA">{dados.modelo || "não escolhida"}</Linha>
                <Linha rotulo="Emoji">{EMOJIS.find((e) => e.valor === dados.emojis)?.rotulo}</Linha>
                <Linha rotulo="Ferramentas">
                  {dados.ferramentas.length === 0
                    ? "nenhuma"
                    : dados.ferramentas
                        .map((n) => ferramentas.find((f) => f.nome === n)?.rotulo ?? n)
                        .join(", ")}
                </Linha>
              </dl>
              {CANAIS[dados.canal] && dados.canal !== "nativo" && (
                <p className="mt-6 text-sm leading-snug text-muted">
                  O agente nasce inativo e a lista mostra que falta conectar. Você conecta pela ficha
                  dele, quando tiver em mãos: {CANAIS[dados.canal].exige.toLowerCase()}
                </p>
              )}
            </Pergunta>
          )}
        </div>

        <div className="hidden lg:block">
          <Previa
            escolhas={{
              nome: dados.nome,
              empresa: empresaEscolhida?.nome ?? dados.empresaNova,
              funcao: dados.funcao,
              emojis: dados.emojis,
              partes: dados.partes,
              buffer: dados.buffer,
              busca: dados.ferramentas.some((f) => f.includes("busca") || f.includes("web")),
            }}
          />
        </div>
      </div>
    </Modal>
  );
}

function Pergunta({
  titulo,
  ajuda,
  children,
}: {
  titulo: string;
  ajuda: string;
  children: React.ReactNode;
}) {
  return (
    <section>
      <h3 className="text-xl font-semibold leading-snug text-texto">{titulo}</h3>
      <p className="mt-1 max-w-[60ch] text-sm text-muted">{ajuda}</p>
      <div className="mt-6">{children}</div>
    </section>
  );
}

function Escolha({
  marcada,
  aoMarcar,
  explica,
  children,
}: {
  marcada: boolean;
  aoMarcar: () => void;
  explica?: string;
  children: React.ReactNode;
}) {
  return (
    <button
      onClick={aoMarcar}
      aria-pressed={marcada}
      className={`flex items-start gap-3 border p-3 text-left transition-colors ${
        marcada ? "border-ciano bg-ciano/5" : "border-borda hover:border-dim"
      }`}
    >
      <span
        className={`mt-0.5 flex h-4 w-4 shrink-0 items-center justify-center border ${
          marcada ? "border-ciano" : "border-dim"
        }`}
      >
        {marcada && <span className="h-2 w-2 bg-ciano" />}
      </span>
      <span>
        <span className="block text-sm text-texto">{children}</span>
        {explica && <span className="mt-0.5 block text-sm text-muted">{explica}</span>}
      </span>
    </button>
  );
}

function Deslizante({
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
        <span className="font-mono text-sm text-texto">
          {valor} {unidade}
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

function Linha({ rotulo, children }: { rotulo: string; children: React.ReactNode }) {
  return (
    <div className="flex items-baseline justify-between gap-6 py-3">
      <dt className="rotulo">{rotulo}</dt>
      <dd className="text-right text-sm text-texto">{children}</dd>
    </div>
  );
}
