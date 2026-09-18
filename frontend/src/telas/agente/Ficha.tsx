import { useCallback, useEffect, useState } from "react";
import {
  api,
  ErroDaApi,
  type Agente,
  type EdicaoDoAgente,
  type Ferramenta,
  type Modelos,
  type NivelDeEmoji,
  type Prompt,
} from "../../api/cliente";
import { Aviso } from "../../design/Aviso";
import { Botao } from "../../design/Botao";
import { Campo } from "../../design/Campo";
import { Carregando } from "../../design/Carregando";
import { Icone } from "../../design/Icone";
import { Interruptor } from "../../design/Interruptor";
import { Marca } from "../../design/Marca";
import { Modal } from "../../design/Modal";
import { Selo } from "../../design/Selo";
import { EscolheIA } from "./EscolheIA";
import { CANAIS, ROTULO_DO_CANAL } from "./canais";
import { Teste } from "./Teste";

/** A ficha do agente, no mesmo popup do onboarding: a lista fica embaçada atrás.
 *
 *  Seis abas, e **cada seção tem o próprio salvar**. Salvar diz o que mudou, não um "pronto"
 *  genérico: quem mexeu em três campos quer saber quais três foram para o banco.
 *
 *  A sexta aba é Conversar: falar com o agente é o jeito de conferir uma mudança antes de ela
 *  chegar em alguém, e isso pertence ao agente, não à lista de conversas.
 */

const ABAS = [
  "perfil",
  "comunicacao",
  "trabalho",
  "ferramentas",
  "configuracoes",
  "conversar",
] as const;
type Aba = (typeof ABAS)[number];

const NOME_DA_ABA: Record<Aba, string> = {
  perfil: "Perfil",
  comunicacao: "Comunicação",
  trabalho: "Trabalho",
  ferramentas: "Ferramentas e integrações",
  configuracoes: "Configurações",
  conversar: "Conversar",
};

const EMOJIS: { valor: NivelDeEmoji; rotulo: string }[] = [
  { valor: "nenhum", rotulo: "Nenhum" },
  { valor: "pouco", rotulo: "Pouco" },
  { valor: "medio", rotulo: "Médio" },
  { valor: "muito", rotulo: "Muito" },
];

const FUNCOES = [
  { valor: "atendimento", rotulo: "Atendimento" },
  { valor: "suporte", rotulo: "Suporte" },
  { valor: "vendas", rotulo: "Vendas" },
] as const;

/** O que cada campo se chama quando o salvar diz o que mudou. */
const NOME_DO_CAMPO: Record<string, string> = {
  nome: "o nome",
  ativo: "a situação",
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
}: {
  agenteId: string;
  aoFechar: () => void;
  aoMudar: () => void;
}) {
  const [agente, setAgente] = useState<Agente | null>(null);
  const [aba, setAba] = useState<Aba>("perfil");
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

  return (
    <Modal
      titulo={agente?.nome ?? "Agente"}
      subtitulo={
        agente ? `${ROTULO_DO_CANAL(agente.canal)}, em ${agente.empresa}` : "abrindo a ficha"
      }
      aoFechar={aoFechar}
    >
      {erro ? (
        <div>
          <Aviso tom="erro" titulo="a ficha não abriu">
            {erro}
          </Aviso>
          <div className="mt-4">
            <Botao pequeno icone="sys-refresh" onClick={() => setTentativa((t) => t + 1)}>
              Tentar de novo
            </Botao>
          </div>
        </div>
      ) : !agente ? (
        <Carregando tipo="anel" o_que="abrindo a ficha" />
      ) : (
        <>
          <nav className="flex gap-1 overflow-x-auto border-b border-borda" role="tablist">
            {ABAS.map((a) => (
              <button
                key={a}
                role="tab"
                aria-selected={aba === a}
                onClick={() => setAba(a)}
                className={`whitespace-nowrap border-b-2 px-4 py-3 text-sm transition-colors ${
                  aba === a
                    ? "border-b-ciano text-ciano"
                    : "border-b-transparent text-muted hover:text-texto"
                }`}
              >
                {NOME_DA_ABA[a]}
              </button>
            ))}
          </nav>

          <div className="mt-8">
            {aba === "perfil" && (
              <Perfil agente={agente} atualiza={atualiza} aoRemover={aoFechar} aoListar={aoMudar} />
            )}
            {aba === "comunicacao" && <Comunicacao agente={agente} atualiza={atualiza} />}
            {aba === "trabalho" && <Trabalho agente={agente} atualiza={atualiza} />}
            {aba === "ferramentas" && <Ferramentas agente={agente} atualiza={atualiza} />}
            {aba === "configuracoes" && <Configuracoes agente={agente} atualiza={atualiza} />}
            {aba === "conversar" && (
              <section>
                <Teste agenteId={agente.id} agente={agente.nome} />
              </section>
            )}
          </div>
        </>
      )}
    </Modal>
  );
}

/** O salvar de cada seção: manda só o que mudou e conta o que foi. */
function useSalvar(agente: Agente, atualiza: (a: Agente) => void) {
  const [salvando, setSalvando] = useState(false);
  const [feito, setFeito] = useState("");
  const [erro, setErro] = useState("");

  async function salva(mudancas: Partial<EdicaoDoAgente>) {
    const sujas = Object.entries(mudancas).filter(
      ([campo, valor]) =>
        JSON.stringify(valor) !== JSON.stringify((agente as unknown as Record<string, unknown>)[campo]),
    );
    if (sujas.length === 0) {
      setFeito("nada mudou");
      return;
    }
    setSalvando(true);
    setErro("");
    try {
      const novo = await api.editaAgente(agente.id, Object.fromEntries(sujas));
      atualiza(novo);
      const nomes = sujas.map(([campo]) => NOME_DO_CAMPO[campo] ?? campo);
      setFeito(`salvei ${nomes.join(", ")}`);
    } catch (problema) {
      setErro(problema instanceof ErroDaApi ? problema.message : String(problema));
    } finally {
      setSalvando(false);
    }
  }

  return { salva, salvando, feito, erro };
}

/** O salvar de cada aba diz o que ele salva: numa ficha de seis abas, "Salvar" sozinho não conta
 *  qual das seis vai para o banco. */
function Rodape({
  rotulo,
  salvando,
  feito,
  erro,
  aoSalvar,
}: {
  rotulo: string;
  salvando: boolean;
  feito: string;
  erro: string;
  aoSalvar: () => void;
}) {
  return (
    <div className="mt-8 flex flex-wrap items-center gap-4 border-t border-borda pt-6">
      <Botao tom="solido" pequeno icone="act-save" ocupado={salvando} onClick={aoSalvar}>
        {rotulo}
      </Botao>
      {erro ? (
        <span className="text-sm text-perigo">{erro}</span>
      ) : (
        feito && <span className="text-sm text-ok">{feito}</span>
      )}
    </div>
  );
}

function Perfil({
  agente,
  atualiza,
  aoRemover,
  aoListar,
}: {
  agente: Agente;
  atualiza: (a: Agente) => void;
  aoRemover: () => void;
  aoListar: () => void;
}) {
  const [nome, setNome] = useState(agente.nome);
  const [ativo, setAtivo] = useState(agente.ativo);
  const [confirmacao, setConfirmacao] = useState("");
  const [removendo, setRemovendo] = useState(false);
  const [erroRemover, setErroRemover] = useState("");
  const [copiado, setCopiado] = useState(false);
  const { salva, salvando, feito, erro } = useSalvar(agente, atualiza);
  const marca = CANAIS[agente.canal]?.marca;

  function copiaEndereco() {
    navigator.clipboard?.writeText(agente.url_webhook ?? "");
    setCopiado(true);
    setTimeout(() => setCopiado(false), 2000);
  }

  async function remove() {
    setRemovendo(true);
    setErroRemover("");
    try {
      await api.removeAgente(agente.id, confirmacao);
      aoListar();
      aoRemover();
    } catch (problema) {
      setErroRemover(problema instanceof ErroDaApi ? problema.message : String(problema));
    } finally {
      setRemovendo(false);
    }
  }

  return (
    <section>
      <Campo rotulo="Nome" value={nome} onChange={(e) => setNome(e.target.value)} />

      <div className="mt-6">
        <Interruptor
          ligado={ativo}
          aoMudar={setAtivo}
          rotulo="Agente ativo"
          descricao="Desligado, ele fica calado: a mensagem continua chegando, e ninguém responde."
        />
      </div>

      <dl className="mt-6 flex flex-col divide-y divide-borda rounded-lg border border-borda px-4">
        <Linha rotulo="Empresa">{agente.empresa}</Linha>
        <Linha rotulo="Canal">
          <span className="inline-flex items-center gap-2">
            {marca && <Marca nome={marca} tamanho={16} apagada={!agente.ativo} />}
            {ROTULO_DO_CANAL(agente.canal)}
          </span>
        </Linha>
        <Linha rotulo="Criado em">
          {new Date(agente.criado_em).toLocaleDateString("pt-BR")}
        </Linha>
      </dl>

      {agente.url_webhook && (
        <div className="mt-6">
          <p className="rotulo">Endereço que o canal chama</p>
          <div className="mt-2 flex flex-wrap items-center gap-3">
            <code className="tecnico min-w-0 flex-1 break-all rounded-md border border-borda bg-void px-3 py-2 text-muted">
              {agente.url_webhook}
            </code>
            <Botao pequeno icone={copiado ? "act-check" : "act-copy"} onClick={copiaEndereco}>
              {copiado ? "Copiado" : "Copiar"}
            </Botao>
          </div>
          <p className="mt-2 text-sm text-dim">
            Quem tiver este endereço fala com o agente. Trate como senha.
          </p>
        </div>
      )}

      <Rodape
        rotulo="Salvar o perfil"
        salvando={salvando}
        feito={feito}
        erro={erro}
        aoSalvar={() => salva({ nome, ativo })}
      />

      <div className="mt-10 rounded-lg border border-perigo/30 p-5">
        <p className="text-sm text-texto">Remover o agente</p>
        <p className="mt-1 text-sm text-muted">
          Ele para de atender e o endereço do canal deixa de valer. As conversas e o consumo ficam
          guardados.
        </p>
        <div className="mt-4 flex flex-wrap items-end gap-3">
          <div className="min-w-[14rem] flex-1">
            <Campo
              rotulo={`Digite ${agente.nome} para confirmar`}
              value={confirmacao}
              onChange={(e) => setConfirmacao(e.target.value)}
            />
          </div>
          <Botao
            tom="perigo"
            pequeno
            icone="act-delete"
            ocupado={removendo}
            disabled={confirmacao !== agente.nome}
            onClick={remove}
          >
            Remover
          </Botao>
        </div>
        {erroRemover && <p className="mt-3 text-sm text-perigo">{erroRemover}</p>}
      </div>
    </section>
  );
}

function Comunicacao({ agente, atualiza }: { agente: Agente; atualiza: (a: Agente) => void }) {
  const [emojis, setEmojis] = useState<NivelDeEmoji>(agente.emojis as NivelDeEmoji);
  const [partes, setPartes] = useState(agente.max_mensagens_por_resposta);
  const [buffer, setBuffer] = useState(agente.buffer_segundos);
  const [velocidade, setVelocidade] = useState(agente.digitacao_caracteres_por_segundo);
  const [teto, setTeto] = useState(agente.digitacao_maximo_segundos);
  const { salva, salvando, feito, erro } = useSalvar(agente, atualiza);

  return (
    <section>
      <p className="rotulo">Emoji</p>
      <div className="mt-2 flex flex-wrap gap-2">
        {EMOJIS.map((e) => (
          <button
            key={e.valor}
            onClick={() => setEmojis(e.valor)}
            className={`rounded-md border px-4 py-2 text-sm transition-colors ${
              emojis === e.valor ? "border-ciano text-ciano" : "border-borda text-muted hover:text-texto"
            }`}
          >
            {e.rotulo}
          </button>
        ))}
      </div>
      {agente.emojis === "livre" && (
        <p className="mt-2 text-sm text-dim">
          Criado antes desta escolha, ele usa emoji como quiser. O que você escolher vale na próxima
          resposta.
        </p>
      )}

      <div className="mt-8 grid gap-6 sm:grid-cols-2">
        <Numero
          rotulo="Dividir a resposta em até"
          valor={partes}
          min={1}
          max={10}
          unidade="mensagens"
          aoMudar={setPartes}
        />
        <Numero
          rotulo="Esperar antes de responder"
          valor={buffer}
          min={1}
          max={60}
          unidade="segundos"
          aoMudar={setBuffer}
          ajuda="Tempo para a pessoa terminar de escrever."
        />
        <Numero
          rotulo="Velocidade de digitação"
          valor={velocidade}
          min={1}
          max={30}
          unidade="caracteres por segundo"
          aoMudar={setVelocidade}
        />
        <Numero
          rotulo="Mostrar digitando por no máximo"
          valor={teto}
          min={1}
          max={30}
          unidade="segundos por mensagem"
          aoMudar={setTeto}
        />
      </div>

      <Rodape
        rotulo="Salvar o jeito de falar"
        salvando={salvando}
        feito={feito}
        erro={erro}
        aoSalvar={() =>
          salva({
            emojis,
            max_mensagens_por_resposta: partes,
            buffer_segundos: buffer,
            digitacao_caracteres_por_segundo: velocidade,
            digitacao_maximo_segundos: teto,
          })
        }
      />
    </section>
  );
}

function Trabalho({ agente, atualiza }: { agente: Agente; atualiza: (a: Agente) => void }) {
  const [prompt, setPrompt] = useState<Prompt | null>(null);
  const [funcao, setFuncao] = useState(agente.perfil?.funcao ?? "");
  const [publico, setPublico] = useState(agente.perfil?.publico ?? "");
  const [site, setSite] = useState(agente.perfil?.site ?? "");
  const [sobre, setSobre] = useState(agente.perfil?.sobre_empresa ?? "");
  const [assina, setAssina] = useState(agente.assina_nome);
  const [aberto, setAberto] = useState(false);
  const [aMao, setAMao] = useState("");
  const [salvando, setSalvando] = useState(false);
  const [feito, setFeito] = useState("");
  const [erro, setErro] = useState("");

  useEffect(() => {
    api
      .prompt(agente.id)
      .then((p) => {
        setPrompt(p);
        setAMao(p.texto);
      })
      .catch((problema) => setErro(problema.message));
  }, [agente.id]);

  async function salvaFormulario() {
    setSalvando(true);
    setErro("");
    try {
      const resposta = await api.gravaPerfil(agente.id, {
        funcao: (funcao || null) as "suporte" | "vendas" | "atendimento" | null,
        publico: publico || null,
        site: site || null,
        sobre_empresa: sobre || null,
        assina_nome: assina,
      });
      atualiza(resposta.agente);
      setAMao(resposta.prompt);
      setPrompt((p) => (p ? { ...p, texto: resposta.prompt, gerado: resposta.prompt } : p));
      setFeito("salvei o perfil e reescrevi o prompt");
    } catch (problema) {
      setErro(problema instanceof ErroDaApi ? problema.message : String(problema));
    } finally {
      setSalvando(false);
    }
  }

  async function salvaAMao() {
    setSalvando(true);
    setErro("");
    try {
      const resposta = await api.gravaPrompt(agente.id, aMao);
      setPrompt((p) => (p ? { ...p, texto: resposta.texto } : p));
      setFeito("salvei o prompt");
    } catch (problema) {
      setErro(problema instanceof ErroDaApi ? problema.message : String(problema));
    } finally {
      setSalvando(false);
    }
  }

  return (
    <section>
      <p className="max-w-[70ch] text-sm text-muted">
        O que você responde aqui vira o prompt do agente.
      </p>

      <div className="mt-6">
        <p className="rotulo">O que ele faz</p>
        <div className="mt-2 flex flex-wrap gap-2">
          {FUNCOES.map((f) => (
            <button
              key={f.valor}
              onClick={() => setFuncao(f.valor)}
              className={`rounded-md border px-4 py-2 text-sm transition-colors ${
                funcao === f.valor ? "border-ciano text-ciano" : "border-borda text-muted hover:text-texto"
              }`}
            >
              {f.rotulo}
            </button>
          ))}
        </div>
      </div>

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

      <div className="mt-4">
        <Interruptor
          ligado={assina}
          aoMudar={setAssina}
          rotulo="Assinar o nome do agente"
          descricao="Ele acrescenta o próprio nome no fim da resposta."
        />
      </div>

      <div className="mt-8 flex flex-wrap items-center gap-4 border-t border-borda pt-6">
        <Botao tom="solido" pequeno icone="act-save" ocupado={salvando} onClick={salvaFormulario}>
          Salvar e reescrever o prompt
        </Botao>
        {erro ? (
          <span className="text-sm text-perigo">{erro}</span>
        ) : (
          feito && <span className="text-sm text-ok">{feito}</span>
        )}
      </div>

      <div className="mt-8 rounded-lg border border-borda">
        <button
          onClick={() => setAberto((a) => !a)}
          className="flex w-full items-center justify-between gap-4 p-4 text-left"
          aria-expanded={aberto}
        >
          <span className="text-sm text-texto">Ver o que o agente vai ler</span>
          <Icone
            nome="sys-chevron-baixo"
            className={`text-dim transition-transform ${aberto ? "rotate-180" : ""}`}
          />
        </button>
        {aberto && (
          <div className="border-t border-borda p-4">
            {prompt === null ? (
              <Carregando tipo="pontos" o_que="lendo o prompt" mudo />
            ) : (
              <>
                <textarea
                  rows={10}
                  value={aMao}
                  onChange={(e) => setAMao(e.target.value)}
                  aria-label="Prompt do agente"
                  className="w-full rounded-md border border-borda bg-void p-3 font-mono text-xs leading-relaxed text-texto focus:border-ciano focus:outline-none focus:ring-1 focus:ring-ciano"
                />
                <div className="mt-3">
                  <Botao pequeno icone="act-save" ocupado={salvando} onClick={salvaAMao}>
                    Salvar o prompt
                  </Botao>
                </div>
              </>
            )}
          </div>
        )}
      </div>
    </section>
  );
}

function Ferramentas({ agente, atualiza }: { agente: Agente; atualiza: (a: Agente) => void }) {
  const [catalogo, setCatalogo] = useState<Ferramenta[] | null>(null);
  const [ligadas, setLigadas] = useState<string[]>(agente.ferramentas);
  const [horas, setHoras] = useState(agente.retomada_automatica_horas ?? 0);
  const { salva, salvando, feito, erro } = useSalvar(agente, atualiza);

  useEffect(() => {
    api.ferramentas().then(setCatalogo).catch(() => setCatalogo([]));
  }, []);

  return (
    <section>
      {catalogo === null ? (
        <Carregando tipo="pontos" o_que="buscando o catálogo" />
      ) : (
        <div className="flex flex-col">
          {catalogo.map((f) => (
            <Interruptor
              key={f.nome}
              ligado={ligadas.includes(f.nome)}
              aoMudar={(liga) =>
                setLigadas(liga ? [...ligadas, f.nome] : ligadas.filter((n) => n !== f.nome))
              }
              rotulo={f.rotulo}
              descricao={f.descricao}
            />
          ))}
          <Interruptor
            ligado
            desligado
            aoMudar={() => {}}
            rotulo="Passar a conversa para uma pessoa"
            descricao="Sempre ligada. O agente chama uma pessoa quando o contato pede ou quando trava."
          />
        </div>
      )}

      <div className="mt-6 max-w-sm">
        <Numero
          rotulo="O agente volta a responder depois de"
          valor={horas}
          min={0}
          max={720}
          unidade={horas === 0 ? "sem prazo" : "horas"}
          aoMudar={setHoras}
          ajuda="Zero deixa a conversa com a pessoa até alguém devolver."
        />
      </div>

      <div className="mt-8 rounded-lg border border-borda p-5 opacity-60">
        <div className="flex items-center justify-between gap-4">
          <p className="text-sm text-texto">Google Agenda</p>
          <Selo>em breve</Selo>
        </div>
        <p className="mt-1 text-sm text-muted">
          Marcar, remarcar e desmarcar compromisso direto na conversa.
        </p>
      </div>

      <Rodape
        rotulo="Salvar as ferramentas"
        salvando={salvando}
        feito={feito}
        erro={erro}
        aoSalvar={() =>
          salva({ ferramentas: ligadas, retomada_automatica_horas: horas === 0 ? null : horas })
        }
      />
    </section>
  );
}

/** As quatro funções de IA que o escolhedor conhece. Função que a API trouxer fora desta lista
 *  cai no campo de texto, para uma função nova não travar a aba. */
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
function Configuracoes({ agente, atualiza }: { agente: Agente; atualiza: (a: Agente) => void }) {
  const [modelos, setModelos] = useState<Modelos | null>(null);
  const [valores, setValores] = useState<Record<string, string>>({
    modelo_conversa: agente.modelo_conversa,
    modelo_fallback: agente.modelo_fallback ?? "",
    modelo_auxiliar: agente.modelo_auxiliar,
    modelo_visao: agente.modelo_visao,
    modelo_transcricao: agente.modelo_transcricao,
  });
  const [contatos, setContatos] = useState(agente.contatos_permitidos.join(", "));
  const [trocando, setTrocando] = useState("");
  const { salva, salvando, feito, erro } = useSalvar(agente, atualiza);

  useEffect(() => {
    api.modelos().then(setModelos).catch(() => setModelos(null));
  }, []);

  function guarda() {
    const mudancas: Partial<EdicaoDoAgente> = {
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
    salva(mudancas);
  }

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
                  <Botao pequeno onClick={() => setTrocando(aberto ? "" : f.campo)}>
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
                          Ficar sem reserva
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

      <div className="mt-8">
        <Campo
          rotulo="Ele atende só estes telefones, separados por vírgula"
          value={contatos}
          onChange={(e) => setContatos(e.target.value)}
          placeholder="vazio atende qualquer pessoa"
        />
      </div>

      <Rodape
        rotulo="Salvar os modelos"
        salvando={salvando}
        feito={feito}
        erro={erro}
        aoSalvar={guarda}
      />
    </section>
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
