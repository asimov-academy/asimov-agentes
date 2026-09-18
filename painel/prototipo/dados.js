/* Dados de exemplo do protótipo. Os campos são os mesmos que a API devolve hoje
   (GET /admin/agentes, GET /admin/consumo, GET /admin/ferramentas), para que ligar
   na API de verdade seja trocar a fonte em painel.js, não reescrever as telas.

   Repositório público: nada de cliente real. Loja Exemplo, Clínica Exemplo, exemplo.com.br. */

const INSTALACAO = {
  dominio: "exemplo.com.br",
  subdominio_bot: "bot.exemplo.com.br",
  subdominio_app: "app.exemplo.com.br",
  versao: "0.17.0",
  modo: "revenda",
  saude: { api: "ok", banco: "ok", redis: "ok", waha: "ok" },
  modelos_padrao: {
    conversa: "openai:gpt-5.1",
    fallback: "anthropic:claude-sonnet-5",
    visao: "openai:gpt-5-mini",
    transcricao: "openai:gpt-4o-transcribe",
  },
};

const CLIENTES = [
  { id: "c1", nome: "Loja Exemplo", slug: "loja-exemplo", agentes: 2 },
  { id: "c2", nome: "Clínica Exemplo", slug: "clinica-exemplo", agentes: 2 },
];

const FERRAMENTAS = [
  { nome: "calculadora", rotulo: "Calculadora", descricao: "Toda conta do agente passa por aqui: o modelo nunca calcula sozinho.", padrao: false },
  { nome: "busca_web", rotulo: "Busca na web", descricao: "Pesquisa na internet quando a resposta não está no prompt nem na base.", padrao: false },
];

const AGENTES = [
  {
    id: "a1", cliente_id: "c1", cliente: "Loja Exemplo", nome: "Ana", slug: "ana",
    canal: "chatwoot", ativo: true,
    buffer_segundos: 8, max_mensagens_por_resposta: 3,
    digitacao_caracteres_por_segundo: 6, digitacao_maximo_segundos: 20,
    modelo_conversa: "openai:gpt-5.1", modelo_fallback: "anthropic:claude-sonnet-5",
    modelo_auxiliar: "openai:gpt-5-mini", modelo_visao: "openai:gpt-5-mini",
    modelo_transcricao: "openai:gpt-4o-transcribe",
    ferramentas: ["calculadora"], emojis: "pouco", contatos_permitidos: [],
    handoff_destino: { tipo: "atendente", nome: "Equipe de vendas" },
    retomada_automatica_horas: 2,
    url_webhook: "https://bot.exemplo.com.br/webhook/chatwoot/hx7…9f2",
    url_privacidade: "https://bot.exemplo.com.br/privacidade/loja-exemplo/ana",
    conta: "Loja Exemplo · caixa Vendas",
  },
  {
    id: "a2", cliente_id: "c1", cliente: "Loja Exemplo", nome: "Bia", slug: "bia",
    canal: "whatsapp", ativo: true,
    buffer_segundos: 10, max_mensagens_por_resposta: 2,
    digitacao_caracteres_por_segundo: 7, digitacao_maximo_segundos: 20,
    modelo_conversa: "openai:gpt-5.1", modelo_fallback: "",
    modelo_auxiliar: "openai:gpt-5-nano", modelo_visao: "openai:gpt-5-mini",
    modelo_transcricao: "openai:gpt-4o-transcribe",
    ferramentas: ["calculadora", "busca_web"], emojis: "medio", contatos_permitidos: [],
    handoff_destino: { tipo: "numero", numero: "55 51 9xxxx-0001", template: "aviso_handoff" },
    retomada_automatica_horas: 4,
    url_webhook: "https://bot.exemplo.com.br/webhook/whatsapp/k2p…7ab",
    url_privacidade: "https://bot.exemplo.com.br/privacidade/loja-exemplo/bia",
    conta: "Número oficial 55 51 3xxx-0000",
  },
  {
    id: "a3", cliente_id: "c2", cliente: "Clínica Exemplo", nome: "Caio", slug: "caio",
    canal: "waha", ativo: true,
    buffer_segundos: 8, max_mensagens_por_resposta: 3,
    digitacao_caracteres_por_segundo: 6, digitacao_maximo_segundos: 20,
    modelo_conversa: "gemini:gemini-2.5-flash", modelo_fallback: "",
    modelo_auxiliar: "gemini:gemini-2.5-flash", modelo_visao: "gemini:gemini-2.5-flash",
    modelo_transcricao: "groq:whisper-large-v3-turbo",
    ferramentas: [], emojis: "nenhum", contatos_permitidos: ["5551900000002"],
    handoff_destino: { tipo: "grupo", nome: "Recepção" },
    retomada_automatica_horas: 3,
    url_webhook: "http://api:8000/webhook/waha/9dd…c41 (rede interna)",
    url_privacidade: "https://bot.exemplo.com.br/privacidade/clinica-exemplo/caio",
    conta: "Número pareado 55 51 9xxxx-0002",
    waha: { status: "WORKING", numero: "55 51 9xxxx-0002", desde: "2026-09-16T09:12:00" },
  },
  {
    id: "a4", cliente_id: "c2", cliente: "Clínica Exemplo", nome: "Duda", slug: "duda",
    canal: "nativo", ativo: true,
    buffer_segundos: 4, max_mensagens_por_resposta: 3,
    digitacao_caracteres_por_segundo: 12, digitacao_maximo_segundos: 6,
    modelo_conversa: "anthropic:claude-sonnet-5", modelo_fallback: "",
    modelo_auxiliar: "anthropic:claude-haiku-4-5", modelo_visao: "anthropic:claude-sonnet-5",
    modelo_transcricao: "openai:gpt-4o-transcribe",
    ferramentas: ["calculadora"], emojis: "nenhum", contatos_permitidos: [],
    handoff_destino: null, retomada_automatica_horas: null,
    url_webhook: "", url_privacidade: "",
    conta: "Só no terminal e no painel",
  },
];

const CONVERSAS = [
  { id: "v1", agente_id: "a2", agente: "Bia", cliente: "Loja Exemplo", canal: "whatsapp",
    contato: "Contato 0001", telefone: "55 51 9xxxx-0001", status: "agente",
    ultima: "2026-09-18T14:38:00", mensagens: 14, respondendo: true },
  { id: "v2", agente_id: "a1", agente: "Ana", cliente: "Loja Exemplo", canal: "chatwoot",
    contato: "Contato 0002", telefone: "55 51 9xxxx-0002", status: "humano",
    ultima: "2026-09-18T14:31:00", mensagens: 22, respondendo: false,
    handoff: { motivo: "pediu falar com pessoa", codigo: "K7QP", aberto_em: "2026-09-18T14:29:00", destino: "Equipe de vendas" } },
  { id: "v3", agente_id: "a3", agente: "Caio", cliente: "Clínica Exemplo", canal: "waha",
    contato: "Contato 0003", telefone: "55 51 9xxxx-0003", status: "agente",
    ultima: "2026-09-18T14:22:00", mensagens: 6, respondendo: false },
  { id: "v4", agente_id: "a2", agente: "Bia", cliente: "Loja Exemplo", canal: "whatsapp",
    contato: "Contato 0004", telefone: "55 51 9xxxx-0004", status: "agente",
    ultima: "2026-09-18T13:57:00", mensagens: 9, respondendo: false },
  { id: "v5", agente_id: "a3", agente: "Caio", cliente: "Clínica Exemplo", canal: "waha",
    contato: "Contato 0005", telefone: "55 51 9xxxx-0005", status: "humano",
    ultima: "2026-09-18T11:40:00", mensagens: 31, respondendo: false,
    handoff: { motivo: "remarcar consulta", codigo: "M3ZT", aberto_em: "2026-09-18T11:38:00", destino: "Recepção" } },
];

const MENSAGENS = {
  v2: [
    { autor: "contato", texto: "Oi, vocês entregam em Porto Alegre?", hora: "14:20" },
    { autor: "agente", texto: "Oi! Entregamos sim em Porto Alegre e região metropolitana.", hora: "14:20" },
    { autor: "agente", texto: "O prazo é de 2 a 3 dias úteis. Quer que eu calcule o frete para o seu CEP?", hora: "14:21" },
    { autor: "contato", texto: "Quero. 90000-000", hora: "14:24" },
    { autor: "agente", texto: "Para esse CEP o frete fica em R$ 24,90, com entrega até sexta.", hora: "14:24", ferramentas: ["calculadora"] },
    { autor: "contato", texto: "Consigo falar com alguém? Preciso de nota fiscal com CNPJ", hora: "14:28" },
    { autor: "sistema", texto: "Passado para atendimento humano · motivo: pediu falar com pessoa · código K7QP", hora: "14:29" },
    { autor: "atendente", texto: "Oi, aqui é a equipe de vendas. Me passa o CNPJ que eu emito agora.", hora: "14:31" },
  ],
};

const CONSUMO = {
  dias: 7,
  total: { turnos: 1284, chamadas: 1602, tokens: 3140000, custo: 41.87, sem_preco: 0 },
  por_agente: [
    { agente: "Bia", cliente: "Loja Exemplo", turnos: 612, chamadas: 790, tokens: 1720000, custo: 24.10 },
    { agente: "Ana", cliente: "Loja Exemplo", turnos: 431, chamadas: 512, tokens: 980000, custo: 12.44 },
    { agente: "Caio", cliente: "Clínica Exemplo", turnos: 208, chamadas: 267, tokens: 402000, custo: 4.91 },
    { agente: "Duda", cliente: "Clínica Exemplo", turnos: 33, chamadas: 33, tokens: 38000, custo: 0.42 },
  ],
  por_dia: [112, 168, 204, 186, 231, 219, 164],
};

const FALHAS = [
  { quando: "2026-09-18T14:02:00", agente: "Caio", tipo: "midia_grande", detalhe: "Arquivo de 26 MB acima do limite de 20 MB; conversa passada para humano." },
  { quando: "2026-09-18T09:14:00", agente: "Bia", tipo: "modelo", detalhe: "Tempo esgotado no provedor; respondeu pelo fallback." },
  { quando: "2026-09-17T18:44:00", agente: "Ana", tipo: "webhook_assinatura", detalhe: "Assinatura do Chatwoot inválida; respondido 200 e registrado." },
];

const TESTE = {
  turno: { modelo: "openai:gpt-5.1", latencia: 2.8, tokens: 1840, custo: 0.0121, ferramentas: ["calculadora"] },
  mensagens: [
    { autor: "contato", texto: "quanto fica 3 parcelas de 249,90?", hora: "14:41" },
    { autor: "agente", texto: "Três parcelas de R$ 249,90 dão R$ 749,70 no total.", hora: "14:41" },
  ],
};

const QR_EXEMPLO = `
  ███████ ▄▄ ▀█▄▀ ▄▄▄ ███████
  █ ▄▄▄ █ ▀█▄█▀▄█▀▄ █ █ ▄▄▄ █
  █ ███ █ █ ▄▀▄▀▄ ▄██ █ ███ █
  █▄▄▄▄▄█ ▄▀█ █▀▄ ▄▀█ █▄▄▄▄▄█
  ▄▄▄▄▄ ▄▄▄▀ ▄█▄█▀▄▄▀▄ ▄ ▄ ▄▄
  █ ▄█▄▀▄ ▄▀█▄ ▀▄█▀▄▄█▀▀▄█▄ ▀
  ▄██▄█▄▄█▀▄ ▄▄▀█ ▄▀▄█▄▄▀▄▀▄█
  █ ▄▄▄ █ ▄█▀▄▀█▄▀▄ ▄█ ▄ █▄▀▄
  █ ███ █ ▀▄█ ▄▀▄█▀▄▄█▄▄▄█▄ █
  █▄▄▄▄▄█ █▄▀ ▄ ▀▄█ ▄▀▄ ▀█▄▄▀
`;
