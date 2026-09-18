import { useCallback, useEffect, useMemo, useState } from "react";
import {
  api,
  ErroDaApi,
  type Agente,
  type Empresa,
  type NivelDeEmoji,
  type TomDeVoz,
} from "../../api/cliente";
import { Aviso } from "../../design/Aviso";
import { Botao } from "../../design/Botao";
import { Campo } from "../../design/Campo";
import { Faixa } from "../../design/Faixa";
import { Icone } from "../../design/Icone";
import { Interruptor } from "../../design/Interruptor";
import { Modal } from "../../design/Modal";
import { Passos } from "../../design/Passos";
import { EscolheIA } from "./EscolheIA";
import { Teste } from "./Teste";

/** O onboarding do agente, no popup grande com o fundo embaçado.
 *
 *  Não há prévia de como ele vai soar: era uma conversa de mentira ocupando um terço do popup, e o
 *  fluxo termina numa conversa de verdade com o agente, que é o que mostra o jeito dele falar.
 *
 *  A ordem é a que o operador desenhou: nome, objetivo, onde ele trabalha, o que a empresa faz e os
 *  ajustes. **Canal não se escolhe aqui.** Todo agente nasce respondendo no painel e no terminal, e
 *  conectar a um WhatsApp ou a um Chatwoot virou um passo depois, na ficha: escolher canal na
 *  criação parava o operador num formulário de credencial antes de ele ter visto o agente falar.
 *
 *  A criação é uma chamada só no fim: passo nenhum grava pela metade, então desistir no meio não
 *  deixa agente capenga no banco. O rascunho fica no navegador, e fechar o popup não perde nada.
 */
const RASCUNHO = "asimov:onboarding";

const PASSOS = ["Nome", "Objetivo", "Empresa", "Sobre", "Jeito"];

type NomeDeIconeDaFuncao = "comm-chat" | "stat-info" | "nav-reports";

const FUNCOES: { valor: string; rotulo: string; explica: string; icone: NomeDeIconeDaFuncao }[] = [
  {
    valor: "atendimento",
    rotulo: "Atendimento",
    explica: "Recebe quem chega, tira dúvidas e encaminha.",
    icone: "comm-chat",
  },
  {
    valor: "suporte",
    rotulo: "Suporte",
    explica: "Resolve problema de quem já é cliente.",
    icone: "stat-info",
  },
  {
    valor: "vendas",
    rotulo: "Vendas",
    explica: "Ajuda quem está decidindo a comprar.",
    icone: "nav-reports",
  },
];

const EMOJIS: { valor: NivelDeEmoji; rotulo: string }[] = [
  { valor: "nenhum", rotulo: "Nenhum" },
  { valor: "pouco", rotulo: "Pouco" },
  { valor: "medio", rotulo: "Médio" },
  { valor: "muito", rotulo: "Muito" },
];

const TONS: { valor: TomDeVoz; rotulo: string; explica: string }[] = [
  { valor: "formal", rotulo: "Formal", explica: "Português correto, sem gíria." },
  { valor: "normal", rotulo: "Normal", explica: "Como alguém da empresa no WhatsApp." },
  { valor: "descontraido", rotulo: "Descontraído", explica: "Leve e próximo, sem perder o profissional." },
];

type Rascunho = {
  nome: string;
  funcao: string;
  empresaId: string;
  empresaNova: string;
  site: string;
  sobre: string;
  emojis: NivelDeEmoji;
  tom: TomDeVoz;
  humano: boolean;
  soDaEmpresa: boolean;
  partes: number;
  buffer: number;
  modelo: string;
};

const VAZIO: Rascunho = {
  nome: "",
  funcao: "atendimento",
  empresaId: "",
  empresaNova: "",
  site: "",
  sobre: "",
  emojis: "nenhum",
  tom: "normal",
  humano: true,
  soDaEmpresa: true,
  partes: 3,
  buffer: 8,
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
  /** A aba em que a ficha abre: o operador acabou de escolher o que quer fazer agora. */
  aoCriar: (agente: Agente, aba?: string) => void;
}) {
  const [passo, setPasso] = useState(0);
  const [dados, setDados] = useState<Rascunho>(leRascunho);
  const [erro, setErro] = useState("");
  const [salvando, setSalvando] = useState(false);
  const [listaDeEmpresas, setListaDeEmpresas] = useState(empresas);
  const [criado, setCriado] = useState<Agente | null>(null);
  // A IA não se escolhe mais na criação: o agente nasce com a da instalação e troca na ficha. Só
  // quando não existe chave nenhuma o passo pede uma, senão o agente nasceria sem conseguir falar.
  const [semChave, setSemChave] = useState(false);

  useEffect(() => {
    api
      .modelos()
      .then((catalogo) => setSemChave(catalogo.com_chave.length === 0))
      .catch(() => setSemChave(false));
  }, []);

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

  const nomeDaEmpresa =
    listaDeEmpresas.find((e) => e.id === dados.empresaId)?.nome || dados.empresaNova;

  const podeAvancar = useMemo(() => {
    if (passo === 0) return Boolean(dados.nome.trim());
    if (passo === 2) return Boolean(nomeDaEmpresa.trim());
    if (passo === 4 && semChave) return dados.modelo.includes(":") && !dados.modelo.endsWith(":");
    return true;
  }, [passo, dados, nomeDaEmpresa, semChave]);

  function avanca() {
    setErro("");
    setPasso((p) => Math.min(p + 1, PASSOS.length - 1));
  }

  async function cria() {
    setErro("");
    setSalvando(true);
    try {
      // A empresa nasce aqui, e não no passo dela: criar antes deixava empresa órfã toda vez que o
      // operador desistia no meio.
      let empresaId = dados.empresaId;
      if (!empresaId) {
        const existente = listaDeEmpresas.find(
          (e) => e.nome.trim().toLowerCase() === nomeDaEmpresa.trim().toLowerCase(),
        );
        const empresa = existente ?? (await api.criaEmpresa(nomeDaEmpresa.trim()));
        if (!existente) setListaDeEmpresas((antes) => [...antes, empresa]);
        empresaId = empresa.id;
      }

      const agente = await api.criaAgente(empresaId, {
        nome: dados.nome.trim(),
        // Todo agente nasce no painel e no terminal. Canal externo vem depois, na ficha.
        canal: "nativo",
        emojis: dados.emojis,
        tom: dados.tom,
        transfere_para_humano: dados.humano,
        restringe_temas: dados.soDaEmpresa,
        max_mensagens_por_resposta: dados.partes,
        buffer_segundos: dados.buffer,
        // Ferramenta não se escolhe aqui: o agente nasce cru e ganha ferramenta no treinamento,
        // depois de o operador ver como ele fala.
        // Vazio: o servidor usa a IA que a instalação já tem.
        modelo_conversa: dados.modelo || undefined,
      });
      await api.gravaPerfil(agente.id, {
        funcao: dados.funcao as "suporte" | "vendas" | "atendimento",
        site: dados.site || null,
        sobre_empresa: dados.sobre || null,
      });

      localStorage.removeItem(RASCUNHO);
      setDados(VAZIO);
      setCriado(agente);
    } catch (problema) {
      setErro(problema instanceof ErroDaApi ? problema.message : String(problema));
    } finally {
      setSalvando(false);
    }
  }

  // O fim não é um "pronto": é escolher o próximo passo, e falar com ele é o primeiro deles.
  if (criado) return <Pronto agente={criado} aoIr={(aba) => aoCriar(criado, aba)} />;

  return (
    <Modal
      titulo="Novo agente"
      subtitulo={`Passo ${passo + 1} de ${PASSOS.length}: ${PASSOS[passo]}`}
      aoFechar={aoFechar}
      largura="max-w-4xl"
      rodape={
        <>
          {passo > 0 && (
            <Botao pequeno onClick={() => setPasso((p) => p - 1)}>
              Voltar
            </Botao>
          )}
          {passo < PASSOS.length - 1 ? (
            <Botao tom="acento" pequeno disabled={!podeAvancar} onClick={avanca}>
              Continuar
            </Botao>
          ) : (
            <Botao
              tom="solido"
              pequeno
              icone="act-check"
              ocupado={salvando}
              disabled={!podeAvancar}
              onClick={cria}
            >
              Criar agente
            </Botao>
          )}
        </>
      }
    >
      <div className="grid gap-8 lg:grid-cols-[11rem_1fr]">
        <Passos passos={PASSOS} atual={passo} aoIr={(i) => setPasso(i)} />

        <div className="min-w-0">
          {erro && (
            <div className="mb-5">
              <Aviso tom="erro" titulo="não deu para criar o agente">
                <p>{erro}</p>
              </Aviso>
            </div>
          )}

          {passo === 0 && (
            <Pergunta titulo="Como ele se chama?" ajuda="O nome aparece para quem conversa com ele.">
              <Campo
                rotulo="Nome do agente"
                placeholder="Ana"
                value={dados.nome}
                onChange={(e) => muda("nome", e.target.value)}
                autoFocus
              />
            </Pergunta>
          )}

          {passo === 1 && (
            <Pergunta titulo={`Qual o objetivo de ${dados.nome.trim() || "ele"}?`} ajuda="">
              <div className="grid gap-3 sm:grid-cols-3">
                {FUNCOES.map((f) => {
                  const marcada = dados.funcao === f.valor;
                  return (
                    <button
                      key={f.valor}
                      onClick={() => muda("funcao", f.valor)}
                      aria-pressed={marcada}
                      className={`flex flex-col items-start gap-2 rounded-lg border p-4 text-left transition-colors ${
                        marcada ? "border-ciano bg-ciano/5" : "border-borda hover:border-dim"
                      }`}
                    >
                      <span
                        className={`flex h-10 w-10 items-center justify-center rounded-md border ${
                          marcada ? "border-ciano/40 text-ciano" : "border-borda text-muted"
                        }`}
                      >
                        <Icone nome={f.icone} tamanho={18} />
                      </span>
                      <span className="text-sm font-semibold text-texto">{f.rotulo}</span>
                      <span className="text-sm leading-snug text-muted">{f.explica}</span>
                    </button>
                  );
                })}
              </div>
            </Pergunta>
          )}

          {passo === 2 && (
            <Pergunta
              titulo={`Onde ${dados.nome.trim() || "ele"} vai trabalhar?`}
              ajuda="A empresa que ele atende. Cada uma tem os próprios agentes e conversas."
            >
              <Campo
                rotulo="Nome da empresa"
                placeholder="Loja Exemplo"
                autoFocus
                value={nomeDaEmpresa}
                onChange={(e) => {
                  muda("empresaId", "");
                  muda("empresaNova", e.target.value);
                }}
              />

              {listaDeEmpresas.length > 0 && (
                <div className="mt-3 flex flex-wrap gap-2">
                  {listaDeEmpresas.map((e) => (
                    <button
                      key={e.id}
                      onClick={() => {
                        muda("empresaId", e.id);
                        muda("empresaNova", "");
                      }}
                      aria-pressed={dados.empresaId === e.id}
                      className={`rounded-full border px-3 py-1 text-xs transition-colors ${
                        dados.empresaId === e.id
                          ? "border-ciano text-ciano"
                          : "border-borda text-muted hover:text-texto"
                      }`}
                    >
                      {e.nome}
                    </button>
                  ))}
                </div>
              )}

              <div className="mt-5">
                <Campo
                  rotulo="Site (opcional)"
                  placeholder="https://"
                  value={dados.site}
                  onChange={(e) => muda("site", e.target.value)}
                />
              </div>
            </Pergunta>
          )}

          {passo === 3 && (
            <Sobre empresa={nomeDaEmpresa} texto={dados.sobre} aoMudar={(t) => muda("sobre", t)} />
          )}

          {passo === 4 && (
            <Pergunta titulo={`Como ${dados.nome.trim() || "ele"} fala`} ajuda="">
              <div>
                <p className="rotulo">Tom</p>
                <div className="mt-2 grid gap-2 sm:grid-cols-3">
                  {TONS.map((t) => (
                    <button
                      key={t.valor}
                      onClick={() => muda("tom", t.valor)}
                      aria-pressed={dados.tom === t.valor}
                      className={`rounded-md border px-3 py-2 text-left transition-colors ${
                        dados.tom === t.valor
                          ? "border-ciano bg-ciano/5"
                          : "border-borda hover:border-dim"
                      }`}
                    >
                      <span
                        className={`block text-sm font-semibold ${
                          dados.tom === t.valor ? "text-ciano" : "text-texto"
                        }`}
                      >
                        {t.rotulo}
                      </span>
                      <span className="mt-0.5 block text-xs text-muted">{t.explica}</span>
                    </button>
                  ))}
                </div>
              </div>

              <div className="mt-6 grid gap-5 sm:grid-cols-2">
                <Faixa
                  rotulo="Emoji nas respostas"
                  opcoes={EMOJIS}
                  valor={dados.emojis}
                  aoMudar={(nivel) => muda("emojis", nivel)}
                />

                <label className="block">
                  <span className="rotulo">Dividir a resposta em até</span>
                  <select
                    value={dados.partes}
                    onChange={(e) => muda("partes", Number(e.target.value))}
                    className="mt-2 w-full rounded-md border border-borda bg-surface px-3 py-2 text-sm text-texto focus:border-ciano focus:outline-none"
                  >
                    {[1, 2, 3, 4, 5].map((n) => (
                      <option key={n} value={n}>
                        {n} {n === 1 ? "mensagem" : "mensagens"}
                      </option>
                    ))}
                  </select>
                </label>
              </div>

              <div className="mt-6 flex flex-col border-t border-borda pt-5">
                <Interruptor
                  ligado={dados.humano}
                  aoMudar={(ligado) => muda("humano", ligado)}
                  rotulo="Passar a conversa para uma pessoa"
                  descricao="Desligado, ele nunca promete atendimento humano e atende até o fim sozinho."
                />
                <Interruptor
                  ligado={dados.soDaEmpresa}
                  aoMudar={(ligado) => muda("soDaEmpresa", ligado)}
                  rotulo="Falar só de assuntos da empresa"
                  descricao="Puxou outro assunto, ele volta ao atendimento em uma frase."
                />
              </div>

              {semChave && (
                <div className="mt-6 border-t border-borda pt-5">
                  <p className="rotulo">Falta a chave de uma IA</p>
                  <p className="mt-1 text-sm text-muted">
                    Esta instalação ainda não tem nenhuma. Guarde uma aqui e ela vale para todos os
                    agentes; depois, o que cada um usa fica em Configurações, na ficha dele.
                  </p>
                  <div className="mt-3">
                    <EscolheIA
                      funcao="conversa"
                      valor={dados.modelo}
                      aoMudar={(m) => muda("modelo", m)}
                    />
                  </div>
                </div>
              )}
            </Pergunta>
          )}
        </div>

      </div>
    </Modal>
  );
}

/** O passo da descrição, com o botão que pede à IA para reescrever o que o operador digitou. */
function Sobre({
  empresa,
  texto,
  aoMudar,
}: {
  empresa: string;
  texto: string;
  aoMudar: (texto: string) => void;
}) {
  const [melhorando, setMelhorando] = useState(false);
  const [erro, setErro] = useState("");

  async function melhora() {
    setErro("");
    setMelhorando(true);
    try {
      const { texto: melhorado } = await api.melhoraTexto(texto, empresa);
      aoMudar(melhorado);
    } catch (problema) {
      // Falhou, o operador não perde o que escreveu: o campo continua com o texto dele.
      setErro(problema instanceof ErroDaApi ? problema.message : String(problema));
    } finally {
      setMelhorando(false);
    }
  }

  return (
    <Pergunta
      titulo={`O que ${empresa || "a empresa"} faz?`}
      ajuda={`Isso melhora a inteligência dele sobre ${empresa || "a empresa"}. Pode pular e escrever depois.`}
    >
      <textarea
        rows={7}
        autoFocus
        value={texto}
        onChange={(e) => aoMudar(e.target.value)}
        placeholder="O que ela vende, para quem, desde quando, o que a diferencia."
        className="w-full rounded-md border border-borda bg-surface px-3 py-2 text-sm leading-relaxed text-texto transition-colors placeholder:text-dim focus:border-ciano focus:outline-none focus:ring-1 focus:ring-ciano"
      />

      <div className="mt-3 flex flex-wrap items-center gap-3">
        <Botao
          pequeno
          icone="sys-girando"
          ocupado={melhorando}
          disabled={!texto.trim()}
          onClick={melhora}
        >
          Melhorar com IA
        </Botao>
        <span className="text-xs text-dim">
          Escreva do seu jeito e a IA arruma. Ela não inventa o que você não escreveu.
        </span>
      </div>

      {erro && (
        <div className="mt-4">
          <Aviso tom="atencao" titulo="não deu para melhorar agora">
            <p>{erro}</p>
          </Aviso>
        </div>
      )}
    </Pergunta>
  );
}

/** A tela do fim: três caminhos, e falar com o agente é o primeiro deles. */
function Pronto({ agente, aoIr }: { agente: Agente; aoIr: (aba?: string) => void }) {
  const aoFechar = () => aoIr();
  const [conversando, setConversando] = useState(false);

  return (
    <Modal
      titulo={`${agente.nome} está pronto`}
      subtitulo={`em ${agente.empresa}, respondendo aqui no painel`}
      aoFechar={aoFechar}
      largura="max-w-2xl"
      rodape={
        conversando ? (
          <Botao pequeno onClick={aoFechar}>
            Ver a ficha
          </Botao>
        ) : undefined
      }
    >
      {conversando ? (
        <Teste
          agenteId={agente.id}
          agente={agente.nome}
          primeiraMensagem="Oi, tudo bem? Queria tirar uma dúvida."
        />
      ) : (
        <ul className="flex flex-col gap-2">
          <Caminho
            icone="comm-chat"
            titulo="Conversar com ele agora"
            explica="Veja como ele responde antes de qualquer outra coisa."
            aoIr={() => setConversando(true)}
          />
          <Caminho
            icone="nav-projects"
            titulo="Fazer treinamentos"
            explica="Ensinar o que ele precisa saber: frase, site, vídeo, documento ou uma base."
            aoIr={() => aoIr("treinamento")}
          />
          <Caminho
            icone="cont-link"
            titulo="Conectar a um canal"
            explica="WhatsApp ou Chatwoot. Até lá, ele atende só aqui."
            aoIr={() => aoIr("configuracoes")}
          />
          <Caminho
            icone="nav-settings"
            titulo="Ajustar a ficha dele"
            explica="Prompt, ferramentas, modelos e ritmo das respostas."
            aoIr={aoFechar}
          />
        </ul>
      )}
    </Modal>
  );
}

function Caminho({
  icone,
  titulo,
  explica,
  aoIr,
}: {
  icone: "comm-chat" | "cont-link" | "nav-settings" | "nav-projects";
  titulo: string;
  explica: string;
  aoIr: () => void;
}) {
  return (
    <li>
      <button
        onClick={aoIr}
        className="flex w-full items-center gap-3 rounded-lg border border-borda p-4 text-left transition-colors hover:border-dim hover:bg-surface"
      >
        <span className="flex h-10 w-10 shrink-0 items-center justify-center rounded-md border border-borda text-muted">
          <Icone nome={icone} tamanho={18} />
        </span>
        <span className="min-w-0 flex-1">
          <span className="block text-sm font-medium text-texto">{titulo}</span>
          <span className="block text-sm leading-snug text-muted">{explica}</span>
        </span>
        <Icone nome="sys-chevron" tamanho={16} className="text-dim" />
      </button>
    </li>
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
      {ajuda && <p className="mt-1 max-w-[60ch] text-sm text-muted">{ajuda}</p>}
      <div className="mt-5">{children}</div>
    </section>
  );
}
