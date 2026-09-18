/* Casca, helpers e a camada de dados do painel.

   `api` é o único lugar que sabe de onde vêm os dados. Hoje resolve do `dados.js`;
   quando o painel virar backend, cada método troca o corpo por um fetch na rota
   anotada no comentário e nenhuma tela muda. */

const api = {
  // GET /painel/api/instalacao (health + .env lido pela API)
  instalacao: async () => INSTALACAO,
  // GET /admin/clientes
  clientes: async () => CLIENTES,
  // GET /admin/agentes?cliente_id=
  agentes: async (cliente_id) => AGENTES.filter((a) => !cliente_id || a.cliente_id === cliente_id),
  // GET /admin/clientes/{c}/agentes/{a}
  agente: async (id) => AGENTES.find((a) => a.id === id),
  // PATCH /admin/clientes/{c}/agentes/{a}
  salvaAgente: async (id, campos) => Object.assign(AGENTES.find((a) => a.id === id), campos),
  // GET /admin/ferramentas
  ferramentas: async () => FERRAMENTAS,
  // GET /admin/conversas?cliente_id=&agente_id=&status=   (rota a construir)
  conversas: async (filtro = {}) =>
    CONVERSAS.filter(
      (c) =>
        (!filtro.agente_id || c.agente_id === filtro.agente_id) &&
        (!filtro.status || c.status === filtro.status),
    ),
  // GET /admin/conversas/{id}   (rota a construir)
  conversa: async (id) => ({ ...CONVERSAS.find((c) => c.id === id), mensagens: MENSAGENS[id] || [] }),
  // POST /admin/clientes/{c}/conversas/{id}/retomar
  retomar: async (id) => {
    const c = CONVERSAS.find((v) => v.id === id);
    c.status = "agente";
    delete c.handoff;
    return c;
  },
  // GET /admin/consumo?dias=
  consumo: async () => CONSUMO,
  // GET /admin/falhas   (hoje vêm as 10 últimas junto do consumo)
  falhas: async () => FALHAS,
  // GET/PUT /admin/clientes/{c}/agentes/{a}/prompt   (rota a construir)
  prompt: async () =>
    "Você é a Ana, atendente da Loja Exemplo.\n\nResponda curto, em português do Brasil, sem inventar\npreço nem prazo. Quando não souber, use a ferramenta certa\nou passe para uma pessoa.\n",
  // GET /admin/clientes/{c}/agentes/{a}/waha
  waha: async (id) => (AGENTES.find((a) => a.id === id) || {}).waha,
  // POST /admin/clientes/{c}/agentes/{a}/terminal  e  GET .../terminal/{conversa}
  teste: async () => TESTE,
};

/* Helpers de tela */

const $ = (s, raiz = document) => raiz.querySelector(s);
const $$ = (s, raiz = document) => [...raiz.querySelectorAll(s)];
const esc = (t) => String(t ?? "").replace(/[&<>"]/g, (c) => ({ "&": "&amp;", "<": "&lt;", ">": "&gt;", '"': "&quot;" })[c]);
const reais = (n) => "R$ " + n.toFixed(2).replace(".", ",");
const mil = (n) => n.toLocaleString("pt-BR");

function horaCurta(iso) {
  const d = new Date(iso);
  const hoje = new Date("2026-09-18T15:00:00");
  const mesmoDia = d.toDateString() === hoje.toDateString();
  const hm = d.toTimeString().slice(0, 5);
  return mesmoDia ? hm : `${String(d.getDate()).padStart(2, "0")}/${String(d.getMonth() + 1).padStart(2, "0")} ${hm}`;
}

const CANAIS = {
  chatwoot: "Chatwoot",
  whatsapp: "WhatsApp oficial",
  waha: "WhatsApp (WAHA)",
  nativo: "Nativo",
};

const EMOJIS = { nenhum: "nenhum", pouco: "pouco", medio: "médio", muito: "muito", livre: "sem regra" };

function seloStatus(status, respondendo) {
  if (respondendo) return '<span class="selo"><i class="bolinha pisca"></i>respondendo</span>';
  if (status === "humano") return '<span class="selo alerta"><i class="bolinha"></i>com atendente</span>';
  return '<span class="selo ok"><i class="bolinha"></i>com o agente</span>';
}

function torrada(texto) {
  let t = $(".torrada");
  if (!t) {
    t = document.createElement("div");
    t.className = "torrada";
    document.body.appendChild(t);
  }
  t.textContent = texto;
  t.classList.add("ver");
  clearTimeout(t._t);
  t._t = setTimeout(() => t.classList.remove("ver"), 2200);
}

/* Casca: topo, navegação e rodapé em volta do <main> que a página já escreveu. */

const PAGINAS = [
  ["inicio.html", "Início", "inicio"],
  ["agentes.html", "Agentes", "agentes"],
  ["conversas.html", "Conversas", "conversas"],
  ["consumo.html", "Consumo", "consumo"],
  ["whatsapp.html", "WhatsApp", "whatsapp"],
];

function montaCasca(ativo) {
  const nav = PAGINAS.map(
    ([url, nome, chave]) => `<a href="${url}" class="${chave === ativo ? "ativo" : ""}">${nome}</a>`,
  ).join("");

  document.body.insertAdjacentHTML(
    "afterbegin",
    `<header class="topo">
      <div class="topo-linha">
        <a class="marca" href="inicio.html">
          <span class="ponto">A</span>
          <span>Asimov Agentes<small>${INSTALACAO.subdominio_app}</small></span>
        </a>
        <div class="topo-fim">
          <a class="botao pequeno forte" href="assistente.html">Novo agente</a>
          <a class="botao pequeno" href="index.html" title="Sair">Sair</a>
        </div>
      </div>
      <nav class="nav">${nav}</nav>
    </header>`,
  );

  document.body.insertAdjacentHTML(
    "beforeend",
    `<footer class="rodape">
      Asimov Agentes v${INSTALACAO.versao} · instalação em modo ${INSTALACAO.modo} ·
      webhooks em <span class="mono">${INSTALACAO.subdominio_bot}</span> ·
      protótipo com dados de exemplo
    </footer>`,
  );
}

/* Marca a opção clicada nas listas de escolha e de marcar. */
document.addEventListener("change", (e) => {
  const campo = e.target.closest(".opcao input");
  if (!campo) return;
  const grupo = campo.closest(".opcoes");
  if (campo.type === "radio") $$(".opcao", grupo).forEach((o) => o.classList.remove("marcada"));
  campo.closest(".opcao").classList.toggle("marcada", campo.checked);
});
