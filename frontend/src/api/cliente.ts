/** Único lugar que sabe falar com a API. Tela nenhuma chama `fetch` direto.
 *
 * A sessão é o cookie `HttpOnly` que o login em Jinja2 já grava: o front não guarda token, não lê
 * `localStorage` e não conhece a `CHAVE_API_ADMIN`. Escrita leva o `X-Painel-CSRF` que veio do
 * `GET /painel/api/eu`, que só chega para quem tem a sessão.
 */

export const RAIZ = "/painel/api";
export const ENTRAR = "/painel/entrar";

export class SemSessao extends Error {}

export class ErroDaApi extends Error {
  constructor(
    readonly codigo: number,
    mensagem: string,
    readonly referencia?: string,
  ) {
    super(mensagem);
  }
}

let csrf = "";

export function guardaCsrf(token: string): void {
  csrf = token;
}

async function chama<T>(caminho: string, opcoes: RequestInit = {}): Promise<T> {
  const escrita = (opcoes.method ?? "GET").toUpperCase() !== "GET";
  const resposta = await fetch(RAIZ + caminho, {
    ...opcoes,
    credentials: "same-origin",
    headers: {
      Accept: "application/json",
      ...(escrita
        ? { "Content-Type": "application/json", "X-Painel-CSRF": csrf }
        : {}),
      ...opcoes.headers,
    },
  });

  if (resposta.status === 401) throw new SemSessao("a sessão terminou");
  if (!resposta.ok) {
    const corpo = await resposta.json().catch(() => ({}));
    throw new ErroDaApi(
      resposta.status,
      corpo.detail ?? `a API respondeu ${resposta.status}`,
      corpo.referencia,
    );
  }
  if (resposta.status === 204) return undefined as T;
  return (await resposta.json()) as T;
}

export const api = {
  /** Quem está logado, o que a instalação tem e o token de escrita. */
  eu: () => chama<Eu>("/eu"),

  /** Empresas da instalação, para o seletor da barra do topo. */
  empresas: () => chama<Empresa[]>("/empresas"),

  /** A tela de abertura. Sem empresa, a instalação inteira; o filtro viaja na URL, nunca no corpo. */
  visaoGeral: (dias: Periodo, empresa?: string) =>
    chama<VisaoGeral>(
      `/visao-geral?dias=${dias}` +
        (empresa ? `&cliente_id=${encodeURIComponent(empresa)}` : ""),
    ),

  criaEmpresa: (nome: string) =>
    chama<Empresa>("/empresas", {
      method: "POST",
      body: JSON.stringify({ nome }),
    }),

  /** Lista de agentes. `ativo` sem valor traz todos. */
  agentes: (empresa?: string, ativo?: boolean) => {
    const busca = new URLSearchParams();
    if (empresa) busca.set("cliente_id", empresa);
    if (ativo !== undefined) busca.set("ativo", String(ativo));
    const query = busca.toString();
    return chama<Agente[]>("/agentes" + (query ? `?${query}` : ""));
  },

  agente: (id: string) => chama<Agente>(`/agentes/${id}`),

  /** A criação é uma chamada só, no fim do onboarding: passo nenhum grava pela metade. */
  criaAgente: (empresa: string, dados: NovoAgente) =>
    chama<Agente>(`/empresas/${empresa}/agentes`, {
      method: "POST",
      body: JSON.stringify(dados),
    }),

  editaAgente: (id: string, mudancas: Partial<EdicaoDoAgente>) =>
    chama<Agente>(`/agentes/${id}`, {
      method: "PATCH",
      body: JSON.stringify(mudancas),
    }),

  removeAgente: (id: string, confirmacao: string) =>
    chama<{ removido: boolean; canal_desconectado: boolean }>(
      `/agentes/${id}`,
      {
        method: "DELETE",
        body: JSON.stringify({ confirmacao }),
      },
    ),

  /** As respostas da aba Trabalho. Gravar reescreve o `persona.md` a partir delas. */
  gravaPerfil: (id: string, perfil: PerfilDoAgente) =>
    chama<{ agente: Agente; prompt: string }>(`/agentes/${id}/perfil`, {
      method: "PUT",
      body: JSON.stringify(perfil),
    }),

  prompt: (id: string) => chama<Prompt>(`/agentes/${id}/prompt`),

  gravaPrompt: (id: string, texto: string) =>
    chama<{ texto: string }>(`/agentes/${id}/prompt`, {
      method: "PUT",
      body: JSON.stringify({ texto }),
    }),

  gravaEspaco: (dados: EspacoDeTrabalho) =>
    chama<void>("/espaco", { method: "PUT", body: JSON.stringify(dados) }),

  gravaPerfilDoOperador: (dados: PerfilDoOperador) =>
    chama<void>("/perfil", { method: "PUT", body: JSON.stringify(dados) }),

  /** O kanban inteiro numa chamada: coluna sem cartão e cartão sem coluna não desenham nada. */
  funil: (empresa: string) => chama<Funil>(`/empresas/${empresa}/funil`),

  criaEtapa: (empresa: string, nome: string) =>
    chama<EtapaDoFunil>(`/empresas/${empresa}/funil/etapas`, {
      method: "POST",
      body: JSON.stringify({ nome }),
    }),

  renomeiaEtapa: (empresa: string, id: string, nome: string) =>
    chama<EtapaDoFunil>(`/empresas/${empresa}/funil/etapas/${id}`, {
      method: "PATCH",
      body: JSON.stringify({ nome }),
    }),

  apagaEtapa: (empresa: string, id: string) =>
    chama<void>(`/empresas/${empresa}/funil/etapas/${id}`, {
      method: "DELETE",
    }),

  criaEtiqueta: (empresa: string, nome: string, cor: CorDeEtiqueta) =>
    chama<EtiquetaDoFunil>(`/empresas/${empresa}/funil/etiquetas`, {
      method: "POST",
      body: JSON.stringify({ nome, cor }),
    }),

  apagaEtiqueta: (empresa: string, id: string) =>
    chama<void>(`/empresas/${empresa}/funil/etiquetas/${id}`, {
      method: "DELETE",
    }),

  criaOportunidade: (
    empresa: string,
    dados: Partial<OportunidadeDoFunil> & { titulo: string },
  ) =>
    chama<{ id: string }>(`/empresas/${empresa}/funil/oportunidades`, {
      method: "POST",
      body: JSON.stringify(dados),
    }),

  editaOportunidade: (
    empresa: string,
    id: string,
    mudancas: Record<string, unknown>,
  ) =>
    chama<{ id: string; etapa_id: string }>(
      `/empresas/${empresa}/funil/oportunidades/${id}`,
      {
        method: "PATCH",
        body: JSON.stringify(mudancas),
      },
    ),

  apagaOportunidade: (empresa: string, id: string) =>
    chama<void>(`/empresas/${empresa}/funil/oportunidades/${id}`, {
      method: "DELETE",
    }),

  /** O botão de estrelinha: a IA da instalação reescreve a descrição que o operador digitou. */
  melhoraTexto: (texto: string, empresa: string) =>
    chama<{ texto: string }>("/texto/melhorar", {
      method: "POST",
      body: JSON.stringify({ texto, empresa }),
    }),

  /** Copiloto do painel: o estado numa chamada, e depois só o que a conversa mudou. */
  copiloto: () => chama<EstadoDoCopiloto>("/copiloto"),
  copilotoSessao: () => chama<SessaoDoCopiloto>("/copiloto/sessao"),
  copilotoFala: (texto: string) =>
    chama<SessaoDoCopiloto>("/copiloto/mensagens", {
      method: "POST",
      body: JSON.stringify({ texto }),
    }),
  /** O clique que autoriza. Nada que o copiloto propõe muda sem passar por aqui. */
  copilotoDecide: (proposta: string, aplicar: boolean) =>
    chama<SessaoDoCopiloto>(`/copiloto/propostas/${proposta}`, {
      method: "POST",
      body: JSON.stringify({ aplicar }),
    }),
  copilotoRecomeca: () =>
    chama<SessaoDoCopiloto>("/copiloto/sessao", { method: "DELETE" }),

  ferramentas: () => chama<Ferramenta[]>("/ferramentas"),
  modelos: () => chama<Modelos>("/modelos"),
  modelosDoProvedor: (provedor: string, funcao: string) =>
    chama<string[]>(`/modelos/${provedor}?funcao=${funcao}`),
  /** A chave vai e nunca volta: o backend testa no provedor e guarda cifrada. */
  guardaChave: (provedor: string, chave: string) =>
    chama<void>(`/chaves/${provedor}`, {
      method: "PUT",
      body: JSON.stringify({ chave }),
    }),
  canais: () => chama<CanalDisponivel[]>("/canais"),

  /** A situação de cada canal, uma linha por agente. */
  situacaoDosCanais: (empresa?: string) =>
    chama<LinhaDeCanal[]>(
      "/canais/situacao" + (empresa ? `?cliente_id=${empresa}` : ""),
    ),

  acaoNoCanal: (id: string, acao: "reiniciar" | "qr") =>
    chama<{ situacao?: SituacaoDoCanal; qr?: string | null }>(
      `/agentes/${id}/canal/acao`,
      {
        method: "POST",
        body: JSON.stringify({ acao }),
      },
    ),

  conversas: (
    filtros: { empresa?: string; agente?: string; status?: string } = {},
  ) => {
    const busca = new URLSearchParams();
    if (filtros.empresa) busca.set("cliente_id", filtros.empresa);
    if (filtros.agente) busca.set("agente_id", filtros.agente);
    if (filtros.status) busca.set("status", filtros.status);
    const query = busca.toString();
    return chama<Conversa[]>("/conversas" + (query ? `?${query}` : ""));
  },

  conversa: (id: string) => chama<ConversaAberta>(`/conversas/${id}`),

  retomaConversa: (id: string) =>
    chama<{ retomado: boolean }>(`/conversas/${id}/retomar`, {
      method: "POST",
      body: JSON.stringify({}),
    }),

  contatos: (busca: string, empresa?: string) => {
    const query = new URLSearchParams();
    if (busca) query.set("busca", busca);
    if (empresa) query.set("cliente_id", empresa);
    const texto = query.toString();
    return chama<Contato[]>("/contatos" + (texto ? `?${texto}` : ""));
  },

  contato: (id: string) => chama<ContatoAberto>(`/contatos/${id}`),

  /** Conversa de teste pelo canal nativo: o mesmo `asimov conversar` do terminal. */
  mandaTeste: (id: string, texto: string, conversa?: string) =>
    chama<{ conversa: string; conversa_id: string; agendada: boolean }>(
      `/agentes/${id}/teste`,
      {
        method: "POST",
        body: JSON.stringify({ texto, conversa: conversa ?? null }),
      },
    ),

  leTeste: (id: string, conversa: string, depois: number) =>
    chama<LeituraDoTeste>(
      `/agentes/${id}/teste/${encodeURIComponent(conversa)}?depois=${depois}`,
    ),
};

export type Eu = {
  operador: {
    nome: string;
    email: string;
    criado_em: string;
    ultimo_acesso_em: string | null;
  };
  espaco: EspacoDeTrabalho;
  instalacao: { subdominio_bot: string; subdominio_app: string };
  empresas: number;
  agentes: number;
  csrf: string;
};

export type Empresa = {
  id: string;
  nome: string;
  slug: string;
  ativo: boolean;
};

/** Os três períodos que o backend aceita. Qualquer outro vira 422 lá, de propósito. */
export const PERIODOS = [1, 7, 30] as const;
export type Periodo = (typeof PERIODOS)[number];

export type Ponto = { quando: string; turnos: number };

export type GastoDoModelo = {
  modelo: string;
  chamadas: number;
  tokens: number;
  custo: string;
};

export type FalhaDoPainel = {
  criado_em: string;
  tipo: string;
  /** O resumo curto que o backend monta. O detalhe cru do provedor nunca sai de lá. */
  resumo: string;
  cliente: string | null;
  agente: string | null;
};

export type HandoffAberto = {
  id: string;
  conversa_id: string;
  codigo: string;
  motivo: string;
  canal: string;
  iniciado_em: string;
  retomar_em: string | null;
  vencido: boolean;
  cliente: string;
  agente: string;
};

/** Quanto cada número mudou do período anterior, em por cento. `null` é "sem comparação". */
export type Variacao = {
  conversas: number | null;
  turnos: number | null;
  custo: number | null;
  falhas: number | null;
};

export type Resolucao = {
  conversas: number;
  com_gente: number;
  sozinho: number;
  porcento: number | null;
};

export type TurnosDoAgente = {
  agente: string;
  cliente: string;
  turnos: number;
  custo: string;
};

export type VisaoGeral = {
  dias: number;
  desde: string;
  totais: {
    conversas: number;
    turnos: number;
    /** Decimal em texto: dinheiro não vira float no caminho. */
    custo: string;
    custo_parcial: boolean;
    falhas: number;
    handoffs_vencidos: number;
  };
  variacao: Variacao;
  serie: { por: "hour" | "day"; pontos: Ponto[] };
  modelos: GastoDoModelo[];
  resolucao: Resolucao;
  agentes: TurnosDoAgente[];
  falhas: FalhaDoPainel[];
  handoffs: HandoffAberto[];
  situacao: { cor: "ok" | "atencao" | "perigo"; texto: string };
};

export type Agente = {
  id: string;
  cliente_id: string;
  empresa: string;
  nome: string;
  slug: string;
  canal: string;
  ativo: boolean;
  criado_em: string;
  /** Só na ficha: ele carrega o token do webhook dentro. */
  url_webhook: string | null;
  credenciais: Record<string, unknown>;
  modelo_conversa: string;
  modelo_fallback: string | null;
  modelo_auxiliar: string;
  modelo_visao: string;
  modelo_transcricao: string;
  buffer_segundos: number;
  max_mensagens_por_resposta: number;
  digitacao_caracteres_por_segundo: number;
  digitacao_maximo_segundos: number;
  ferramentas: string[];
  emojis: string;
  tom: TomDeVoz;
  transfere_para_humano: boolean;
  restringe_temas: boolean;
  contatos_permitidos: string[];
  handoff_destino: Record<string, unknown> | null;
  retomada_automatica_horas: number | null;
  perfil: Record<string, string>;
  assina_nome: boolean;
};

export type NivelDeEmoji = "nenhum" | "pouco" | "medio" | "muito";

/** Como o agente fala. Muda o jeito, nunca o conteúdo. */
export type TomDeVoz = "formal" | "normal" | "descontraido";

export type NovoAgente = {
  nome: string;
  canal: string;
  conexao?: Record<string, unknown>;
  handoff_destino?: Record<string, unknown> | null;
  retomada_automatica_horas?: number | null;
  buffer_segundos?: number;
  max_mensagens_por_resposta?: number;
  digitacao_caracteres_por_segundo?: number;
  digitacao_maximo_segundos?: number;
  ferramentas?: string[];
  emojis?: NivelDeEmoji;
  tom?: TomDeVoz;
  transfere_para_humano?: boolean;
  restringe_temas?: boolean;
  contatos_permitidos?: string[];
  /** Só a resposta: resumo, imagem e áudio nascem no mesmo provedor e mudam na ficha. */
  modelo_conversa?: string;
};

export type EdicaoDoAgente = {
  nome: string;
  ativo: boolean;
  emojis: NivelDeEmoji | "livre";
  tom: TomDeVoz;
  transfere_para_humano: boolean;
  restringe_temas: boolean;
  buffer_segundos: number;
  max_mensagens_por_resposta: number;
  digitacao_caracteres_por_segundo: number;
  digitacao_maximo_segundos: number;
  ferramentas: string[];
  contatos_permitidos: string[];
  retomada_automatica_horas: number | null;
  handoff_destino: Record<string, unknown> | null;
  modelo_conversa: string;
  modelo_fallback: string | null;
  modelo_auxiliar: string;
  modelo_visao: string;
  modelo_transcricao: string;
};

export type Ferramenta = {
  nome: string;
  rotulo: string;
  descricao: string;
  padrao: boolean;
};

export type Modelos = {
  provedores: string[];
  provedores_transcricao: string[];
  /** Provedores que já têm chave guardada na instalação. A chave em si nunca vem. */
  com_chave: string[];
  funcoes: {
    campo: string;
    funcao: string;
    rotulo: string;
    obrigatorio: boolean;
  }[];
  padroes: Record<string, string | null>;
};

export type CanalDisponivel = { nome: string; externo: boolean };

/** O espaço de trabalho: como esta instalação se chama e de quem ela é. Uma linha só, como o
 *  operador, e não se confunde com as empresas atendidas, que moram em `Empresa`. */
export type EspacoDeTrabalho = {
  nome: string;
  sigla: string;
  negocio_nome: string;
  negocio_documento: string;
  negocio_email: string;
  negocio_telefone: string;
  negocio_site: string;
};

export type PerfilDoOperador = { nome: string; email: string };

/** O funil de uma empresa: as colunas do kanban, os cartões e as etiquetas, numa chamada só. */
export type EtapaDoFunil = {
  id: string;
  nome: string;
  ordem: number;
  ganha: boolean;
  perdida: boolean;
  /** Soma dos cartões da coluna, como texto decimal. */
  total: string;
};

export type EtiquetaDoFunil = { id: string; nome: string; cor: CorDeEtiqueta };

/** Cor é nome de token da paleta, nunca hexadecimal: um teste recusa cor solta no `src`. */
export type CorDeEtiqueta = "ciano" | "ok" | "atencao" | "perigo" | "muted";

export type OportunidadeDoFunil = {
  id: string;
  etapa_id: string;
  titulo: string;
  valor: string;
  nota: string;
  ordem: number;
  contato_id: string | null;
  contato: string | null;
  etiquetas: string[];
  criado_em: string;
};

export type Funil = {
  etapas: EtapaDoFunil[];
  etiquetas: EtiquetaDoFunil[];
  oportunidades: OportunidadeDoFunil[];
};

export type PerfilDoAgente = {
  funcao?: "suporte" | "vendas" | "atendimento" | null;
  publico?: string | null;
  site?: string | null;
  sobre_empresa?: string | null;
  assina_nome?: boolean;
};

export type Prompt = {
  /** O texto que o modelo recebe hoje. */
  texto: string;
  /** O que o formulário escreveria no lugar dele. */
  gerado: string;
  arquivo: string;
  perfil: Record<string, string>;
};

export type SituacaoDoCanal = {
  cor: "ok" | "atencao" | "perigo" | "neutro";
  resumo: string;
  erro?: string;
  status?: string;
  pareado?: boolean;
  numero?: string | null;
  nome?: string | null;
  url?: string;
  caixas?: number[];
  pode_reiniciar?: boolean;
  pode_refazer_webhook?: boolean;
};

export type LinhaDeCanal = {
  agente_id: string;
  agente: string;
  empresa: string;
  canal: string;
  ativo: boolean;
  situacao: SituacaoDoCanal;
};

export type Conversa = {
  id: string;
  canal: string;
  status: string;
  criado_em: string;
  atualizado_em: string;
  empresa: string;
  agente: string;
  agente_id: string;
  contato_id: string;
  contato: string | null;
  telefone: string | null;
};

export type MensagemDaConversa = {
  id: string;
  criado_em: string;
  direcao: string;
  autor: string;
  tipo: string;
  texto: string | null;
  texto_extraido: string | null;
  anexo: Record<string, unknown> | null;
};

export type TurnoDaConversa = {
  criado_em: string;
  modelo: string;
  funcao: string;
  tokens_entrada: number;
  tokens_saida: number;
  custo_estimado: string | null;
  latencia_ms: number;
  erro: string | null;
};

export type ConversaAberta = Conversa & {
  mensagens: MensagemDaConversa[];
  turnos: TurnoDaConversa[];
};

export type Contato = {
  id: string;
  nome: string | null;
  telefone: string | null;
  ultima_mensagem_em: string;
  empresa: string;
  agente: string;
};

export type ContatoAberto = Contato & {
  id_externo: string;
  criado_em: string;
  conversas: {
    id: string;
    canal: string;
    status: string;
    criado_em: string;
    atualizado_em: string;
  }[];
};

export type LeituraDoTeste = {
  mensagens: { texto?: string | null }[];
  proxima: number;
  digitando: boolean;
  respondendo: boolean;
  turno: Record<string, unknown> | null;
  handoff: Record<string, unknown> | null;
};

export type VinculoDeIa = {
  vinculada: boolean;
  cli: string;
  nome: string;
  assinatura: string;
  conta: string;
  comando: string;
};

export type PropostaDoCopiloto = {
  id: string;
  tipo: string;
  titulo: string;
  resumo: string;
  situacao: "aguardando" | "aplicada" | "recusada" | "falhou";
  resultado?: string;
  campos?: Record<string, unknown>;
  prompt?: string | null;
};

export type MensagemDoCopiloto = {
  autor: "operador" | "copiloto" | "sistema";
  texto: string;
  em: string;
};

export type SessaoDoCopiloto = {
  id: string;
  estado: "parado" | "pensando";
  erro: string;
  mensagens: MensagemDoCopiloto[];
  propostas: PropostaDoCopiloto[];
};

export type EstadoDoCopiloto = {
  vinculo: VinculoDeIa;
  sessao: SessaoDoCopiloto;
};
