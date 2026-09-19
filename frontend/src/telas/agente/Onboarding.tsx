import { useCallback, useEffect, useMemo, useRef, useState } from "react";
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
import { BotaoIcone } from "../../design/BotaoIcone";
import { Campo } from "../../design/Campo";
import { Faixa } from "../../design/Faixa";
import { Icone } from "../../design/Icone";
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

const FUNCOES: { valor: string; rotulo: string; explica: string }[] = [
  {
    valor: "atendimento",
    rotulo: "Atendimento",
    explica: "Recebe quem chega, tira dúvidas e encaminha.",
  },
  {
    valor: "suporte",
    rotulo: "Suporte",
    explica: "Resolve problema de quem já é cliente.",
  },
  {
    valor: "vendas",
    rotulo: "Vendas",
    explica: "Ajuda quem está decidindo a comprar.",
  },
];

const EMOJIS: { valor: NivelDeEmoji; rotulo: string }[] = [
  { valor: "nenhum", rotulo: "Nenhum" },
  { valor: "pouco", rotulo: "Pouco" },
  { valor: "medio", rotulo: "Médio" },
  { valor: "muito", rotulo: "Muito" },
];

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

type Rascunho = {
  nome: string;
  funcao: string;
  empresaId: string;
  empresaNova: string;
  site: string;
  sobre: string;
  emojis: NivelDeEmoji;
  tom: TomDeVoz;
  partes: number;
  ritmo: string;
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
  partes: 3,
  ritmo: "natural",
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
  // A foto espera o agente existir: a criação é uma chamada só, no fim, e agente nenhum é gravado
  // pela metade. Até lá ela mora aqui, e o retrato sai do arquivo local.
  const [foto, setFoto] = useState<File | null>(null);
  const [avisoDaFoto, setAvisoDaFoto] = useState("");
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

  // Até onde os passos deixam ir: o primeiro obrigatório vazio segura os seguintes.
  const alcanca = !dados.nome.trim() ? 0 : !nomeDaEmpresa.trim() ? 2 : PASSOS.length - 1;

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
        transfere_para_humano: true,
        restringe_temas: true,
        max_mensagens_por_resposta: dados.partes,
        ritmo: dados.ritmo,
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

      if (foto) {
        // Foto que não sobe não derruba o agente recém-criado: ele já existe. O aviso vai para a
        // última tela, onde ainda dá para agir.
        try {
          await api.mandaFoto(agente.id, foto);
        } catch (problema) {
          setAvisoDaFoto(problema instanceof ErroDaApi ? problema.message : String(problema));
        }
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

  // O fim não é um "pronto": é escolher o próximo passo, e falar com ele é o primeiro deles.
  if (criado)
    return (
      <Pronto agente={criado} aviso={avisoDaFoto} aoIr={(aba) => aoCriar(criado, aba)} />
    );

  return (
    <Modal
      titulo="Novo agente"
      aoFechar={aoFechar}
      largura="max-w-4xl"
      rodape={
        <>
          {passo > 0 && (
            <Botao className="min-h-11" onClick={() => setPasso((p) => p - 1)}>
              Voltar
            </Botao>
          )}
          {passo < PASSOS.length - 1 ? (
            <Botao tom="solido" className="min-h-11" disabled={!podeAvancar} onClick={avanca}>
              Continuar
            </Botao>
          ) : (
            <Botao
              tom="solido"
              className="min-h-11"
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
        <Passos passos={PASSOS} atual={passo} alcanca={alcanca} aoIr={(i) => setPasso(i)} />

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
              <div className="flex items-center gap-5">
                <Retrato nome={dados.nome} foto={foto} aoTrocar={setFoto} />
                <div className="min-w-[12rem] flex-1">
                  <Campo
                    aria-label="Nome do agente"
                    placeholder="Ana"
                    value={dados.nome}
                    onChange={(e) => muda("nome", e.target.value)}
                    onKeyDown={(e) => e.key === "Enter" && podeAvancar && avanca()}
                    autoFocus
                  />
                </div>
              </div>
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
                      className={`flex flex-col items-start gap-1 rounded-lg border p-4 text-left transition-colors ${
                        marcada ? "border-ciano bg-ciano/5" : "border-borda hover:border-dim"
                      }`}
                    >
                      <span
                        className={`text-sm font-semibold ${marcada ? "text-ciano" : "text-texto"}`}
                      >
                        {f.rotulo}
                      </span>
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
              ajuda="Cada empresa tem os próprios agentes e conversas."
            >
              <Campo
                rotulo="Empresa"
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

              <div className="mt-6">
                <p className="rotulo">Ritmo</p>
                <div className="mt-2 grid gap-2 sm:grid-cols-3">
                  {RITMOS.map((r) => (
                    <button
                      key={r.valor}
                      onClick={() => muda("ritmo", r.valor)}
                      aria-pressed={dados.ritmo === r.valor}
                      className={`rounded-md border px-3 py-2 text-left transition-colors ${
                        dados.ritmo === r.valor
                          ? "border-ciano bg-ciano/5"
                          : "border-borda hover:border-dim"
                      }`}
                    >
                      <span
                        className={`block text-sm font-semibold ${
                          dados.ritmo === r.valor ? "text-ciano" : "text-texto"
                        }`}
                      >
                        {r.rotulo}
                      </span>
                      <span className="mt-0.5 block text-xs text-muted">{r.explica}</span>
                    </button>
                  ))}
                </div>
              </div>

              <div className="mt-6 grid gap-6 sm:grid-cols-2">
                <Faixa
                  rotulo="Emoji"
                  opcoes={EMOJIS}
                  valor={dados.emojis}
                  aoMudar={(nivel) => muda("emojis", nivel)}
                />
                <label className="block">
                  <span className="rotulo">Dividir a resposta em até</span>
                  <select
                    value={dados.partes}
                    onChange={(e) => muda("partes", Number(e.target.value))}
                    className="mt-2 min-h-11 w-full rounded-md border border-borda bg-surface px-3 text-sm text-texto transition-colors focus:border-ciano focus:outline-none"
                  >
                    {[1, 2, 3, 4, 5].map((n) => (
                      <option key={n} value={n}>
                        {n} {n === 1 ? "mensagem" : "mensagens"}
                      </option>
                    ))}
                  </select>
                </label>
              </div>

              {/* Passar para uma pessoa, falar só de assuntos da empresa e lembrar do contato
                  nascem ligados, e mudam na ficha: são interruptores que quase ninguém desliga na
                  criação, e cada um custava uma leitura no meio do fluxo. */}
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

/** A foto do agente antes de ele existir: o retrato sai do arquivo escolhido, e o envio acontece
 *  depois da criação. Sem foto, a inicial do nome, como na lista. */
function Retrato({
  nome,
  foto,
  aoTrocar,
}: {
  nome: string;
  foto: File | null;
  aoTrocar: (arquivo: File | null) => void;
}) {
  const seletor = useRef<HTMLInputElement>(null);
  const [previa, setPrevia] = useState("");

  useEffect(() => {
    if (!foto) return setPrevia("");
    const endereco = URL.createObjectURL(foto);
    setPrevia(endereco);
    return () => URL.revokeObjectURL(endereco);
  }, [foto]);

  return (
    <div className="flex flex-col items-center gap-1">
      <input
        ref={seletor}
        type="file"
        hidden
        accept="image/png,image/jpeg,image/webp"
        onChange={(e) => {
          aoTrocar(e.target.files?.[0] ?? null);
          e.target.value = "";
        }}
      />

      {/* O retrato é o botão, com o selo no canto: em tela de toque não existe passar o mouse. */}
      <div className="relative">
        <button
          onClick={() => seletor.current?.click()}
          aria-label={foto ? "Trocar a foto" : "Enviar uma foto"}
          title={`${foto ? "Trocar a foto" : "Enviar uma foto"}: opcional, PNG, JPEG ou WebP`}
          className="group/foto relative block rounded-md"
        >
          {previa ? (
            <img
              src={previa}
              alt=""
              className="h-24 w-24 rounded-md border border-borda object-cover"
            />
          ) : (
            <span
              aria-hidden="true"
              className="flex h-24 w-24 items-center justify-center rounded-md border border-ciano/40 bg-ciano/10 text-4xl font-semibold text-ciano"
            >
              {nome.trim().slice(0, 1).toUpperCase() || "?"}
            </span>
          )}
          <span className="absolute inset-0 rounded-md bg-void/50 opacity-0 transition-opacity group-hover/foto:opacity-100 group-focus-visible/foto:opacity-100" />
          <span className="absolute -bottom-1 -right-1 flex h-7 w-7 items-center justify-center rounded-full border border-borda bg-panel text-muted transition-colors group-hover/foto:border-ciano group-hover/foto:text-ciano">
            <Icone nome="act-upload" tamanho={14} />
          </span>
        </button>

        {foto && (
          <button
            onClick={() => aoTrocar(null)}
            aria-label="Tirar a foto"
            title="Tirar a foto"
            className="absolute -right-1 -top-1 flex h-7 w-7 items-center justify-center rounded-full border border-borda bg-panel text-muted transition-colors before:absolute before:-inset-2 before:content-[''] hover:border-perigo hover:text-perigo"
          >
            <Icone nome="act-delete" tamanho={14} />
          </button>
        )}
      </div>
    </div>
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
    <Pergunta titulo={`O que ${empresa || "a empresa"} faz?`} ajuda="Opcional. Dá para escrever depois.">
      {/* O botão mora dentro do campo, no canto: é ação sobre este texto, e não mais um bloco. */}
      <div className="relative">
        <textarea
          rows={9}
          autoFocus
          value={texto}
          onChange={(e) => aoMudar(e.target.value)}
          aria-label={`O que ${empresa || "a empresa"} faz`}
          placeholder="O que vende, para quem, desde quando, o que a diferencia."
          className="w-full resize-none rounded-md border border-borda bg-surface px-3 py-2 pb-12 text-sm leading-relaxed text-texto transition-colors placeholder:text-dim focus:border-ciano focus:outline-none focus:ring-1 focus:ring-ciano"
        />
        <span className="absolute bottom-2 right-1.5">
          <BotaoIcone
            icone="act-magic"
            tom="acento"
            rotulo="Melhorar com IA"
            explica="Arruma o que você escreveu, sem inventar nada."
            ocupado={melhorando}
            disabled={!texto.trim()}
            onClick={melhora}
          />
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
function Pronto({
  agente,
  aviso,
  aoIr,
}: {
  agente: Agente;
  /** O que deu errado depois de o agente existir, e por isso não o impediu de nascer. */
  aviso: string;
  aoIr: (aba?: string) => void;
}) {
  const aoFechar = () => aoIr();
  const [conversando, setConversando] = useState(false);

  return (
    <Modal
      titulo={agente.nome}
      subtitulo={`Criado em ${agente.empresa}. Já responde aqui no painel.`}
      aoFechar={aoFechar}
      largura="max-w-4xl"
      rodape={
        conversando ? (
          <Botao className="min-h-11" onClick={aoFechar}>
            Abrir a ficha
          </Botao>
        ) : undefined
      }
    >
      {aviso && (
        <div className="mb-5">
          <Aviso tom="atencao" titulo="a foto não subiu">
            {aviso} Envie outra no Perfil dele.
          </Aviso>
        </div>
      )}

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
            titulo="Conversar com ele"
            explica="Veja como ele responde."
            aoIr={() => setConversando(true)}
          />
          <Caminho
            icone="nav-projects"
            titulo="Treinar"
            explica="Ensine por frase, site ou documento."
            aoIr={() => aoIr("treinamento")}
          />
          <Caminho
            icone="cont-link"
            titulo="Conectar um canal"
            explica="WhatsApp ou Chatwoot. Até lá, ele atende só aqui."
            aoIr={() => aoIr("canais")}
          />
          <Caminho
            icone="nav-settings"
            titulo="Abrir a ficha"
            explica="Prompt, ferramentas, modelos e ritmo."
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
        <Icone nome={icone} tamanho={18} className="shrink-0 text-muted" />
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
