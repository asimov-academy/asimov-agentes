import { useState } from "react";
import { api, ErroDaApi, type Agente, type DescobertaNoCanal } from "../../api/cliente";
import { Aviso } from "../../design/Aviso";
import { Botao } from "../../design/Botao";
import { Campo } from "../../design/Campo";
import { Dica } from "../../design/Dica";
import { Marca } from "../../design/Marca";
import { Selo } from "../../design/Selo";
import { CANAIS, ROTULO_DO_CANAL } from "./canais";

/** A aba Canais da ficha: por onde o agente atende, e como ligá-lo a um canal.
 *
 *  Ligar um agente a um canal só existia no terminal. Desde a v0.24.0 todo agente nasce no nativo,
 *  então quem criava pelo navegador não tinha como fazê-lo atender ninguém: a ficha mostrava o canal
 *  e não deixava mudá-lo. Esta aba é o passo que faltava, com as mesmas perguntas do menu.
 *
 *  **Trocar de canal continua sendo remover e criar de novo** (o serviço recusa), e a aba diz isso
 *  em vez de oferecer um botão que vai falhar.
 */
const LIGAVEIS = ["chatwoot", "waha", "whatsapp"];

function mensagem(problema: unknown): string {
  return problema instanceof ErroDaApi ? problema.message : String(problema);
}

export function Canal({ agente, atualiza }: { agente: Agente; atualiza: (a: Agente) => void }) {
  return agente.canal === "nativo" ? (
    <Ligar agente={agente} atualiza={atualiza} />
  ) : (
    <Ligado agente={agente} />
  );
}

/** O agente já atende por um canal externo: o que está valendo e o que dá para fazer com ele. */
function Ligado({ agente }: { agente: Agente }) {
  const texto = CANAIS[agente.canal];
  const [qr, setQr] = useState<string | null>(null);
  const [ocupado, setOcupado] = useState("");
  const [erro, setErro] = useState("");

  async function acao(qual: "qr" | "reiniciar") {
    setOcupado(qual);
    setErro("");
    try {
      const resposta = await api.acaoNoCanal(agente.id, qual);
      if (qual === "qr") setQr(resposta.qr ?? null);
    } catch (problema) {
      setErro(mensagem(problema));
    } finally {
      setOcupado("");
    }
  }

  return (
    <section>
      <div className="flex flex-wrap items-center gap-3 rounded-lg border border-borda p-5">
        {texto && <Marca nome={texto.marca} tamanho={24} />}
        <span className="min-w-0 flex-1">
          <span className="block text-sm text-texto">{ROTULO_DO_CANAL(agente.canal)}</span>
          {texto && <span className="block text-sm text-muted">{texto.serve}</span>}
        </span>
        <Selo tom="ok">ligado</Selo>
      </div>

      {Object.keys(agente.credenciais).length > 0 && (
        <dl className="mt-4 grid gap-x-8 gap-y-3 rounded-lg border border-borda p-5 sm:grid-cols-2">
          {Object.entries(agente.credenciais).map(([campo, valor]) => (
            <div key={campo} className="min-w-0">
              <dt className="rotulo">{campo.replace(/_/g, " ")}</dt>
              <dd className="tecnico mt-1 truncate text-sm text-texto">{String(valor)}</dd>
            </div>
          ))}
        </dl>
      )}

      {agente.canal === "waha" && (
        <div className="mt-4">
          <p className="rotulo">O número deste agente</p>
          <div className="mt-2 flex flex-wrap gap-3">
            <Botao pequeno icone="cont-image" ocupado={ocupado === "qr"} onClick={() => acao("qr")}>
              Ver o QR code
            </Botao>
            <Botao
              pequeno
              icone="sys-refresh"
              ocupado={ocupado === "reiniciar"}
              onClick={() => acao("reiniciar")}
            >
              Reiniciar a sessão
            </Botao>
          </div>
          {qr && (
            <img
              src={`data:image/png;base64,${qr}`}
              alt="QR code para parear o número"
              className="mt-4 w-56 rounded-md bg-texto p-2"
            />
          )}
          {qr === null && ocupado === "" && erro === "" && (
            <p className="mt-2 text-sm text-dim">
              O QR code só aparece enquanto o número não estiver pareado.
            </p>
          )}
        </div>
      )}

      {erro && (
        <div className="mt-4">
          <Aviso tom="erro" titulo="o canal não respondeu">
            {erro}
          </Aviso>
        </div>
      )}

      <p className="mt-6 text-sm text-dim">
        Para levar este agente a outro canal, remova e crie de novo. O prompt e o jeito de falar
        estão na ficha e voltam com ele; as conversas ficam guardadas.
      </p>
    </section>
  );
}

/** O agente ainda não atende ninguém de fora: escolher o canal e ligá-lo. */
function Ligar({ agente, atualiza }: { agente: Agente; atualiza: (a: Agente) => void }) {
  const [canal, setCanal] = useState("");

  if (!canal) {
    return (
      <section>
        <p className="text-sm text-muted">
          Hoje {agente.nome} só responde aqui e no terminal. Escolha por onde ele vai atender de
          verdade.
        </p>
        <div className="mt-4 grid gap-3 sm:grid-cols-3">
          {LIGAVEIS.map((nome) => {
            const texto = CANAIS[nome];
            return (
              <button
                key={nome}
                onClick={() => setCanal(nome)}
                className="rounded-lg border border-borda p-4 text-left transition-colors hover:border-ciano"
              >
                <Marca nome={texto.marca} tamanho={24} />
                <span className="mt-3 block text-sm text-texto">{texto.rotulo}</span>
                <span className="mt-1 block text-sm text-muted">{texto.serve}</span>
                <span className="mt-3 flex items-center gap-2 text-xs text-dim">
                  precisa de {texto.exige}
                  {texto.atencao && <Dica texto={texto.atencao} />}
                </span>
              </button>
            );
          })}
        </div>
      </section>
    );
  }

  return (
    <section>
      <button
        onClick={() => setCanal("")}
        className="text-sm text-muted underline-offset-2 hover:text-texto hover:underline"
      >
        Escolher outro canal
      </button>
      <div className="mt-4">
        {canal === "chatwoot" && <Chatwoot agente={agente} atualiza={atualiza} />}
        {canal === "waha" && <Waha agente={agente} atualiza={atualiza} />}
        {canal === "whatsapp" && <WhatsApp agente={agente} atualiza={atualiza} />}
      </div>
    </section>
  );
}

/** O botão que liga, com o erro do canal logo abaixo dele. */
function Conectar({
  rotulo,
  desligado,
  ajuda,
  aoConectar,
}: {
  rotulo: string;
  desligado?: boolean;
  ajuda?: string;
  aoConectar: () => Promise<void>;
}) {
  const [ocupado, setOcupado] = useState(false);
  const [erro, setErro] = useState("");

  return (
    <div className="mt-6">
      {erro && (
        <div className="mb-4">
          <Aviso tom="erro" titulo="não deu para ligar">
            {erro}
          </Aviso>
        </div>
      )}
      <div className="flex flex-wrap items-center gap-3">
        <Botao
          tom="solido"
          icone="cont-link"
          ocupado={ocupado}
          disabled={desligado}
          onClick={async () => {
            setOcupado(true);
            setErro("");
            try {
              await aoConectar();
            } catch (problema) {
              setErro(mensagem(problema));
            } finally {
              setOcupado(false);
            }
          }}
        >
          {rotulo}
        </Botao>
        {ajuda && <span className="text-sm text-dim">{ajuda}</span>}
      </div>
    </div>
  );
}

function Chatwoot({ agente, atualiza }: { agente: Agente; atualiza: (a: Agente) => void }) {
  const [url, setUrl] = useState("");
  const [token, setToken] = useState("");
  const [achado, setAchado] = useState<DescobertaNoCanal | null>(null);
  const [procurando, setProcurando] = useState(false);
  const [erro, setErro] = useState("");
  const [conta, setConta] = useState("");
  const [caixas, setCaixas] = useState<number[]>([]);

  const daConta = achado?.contas?.find((c) => String(c.id) === conta);

  async function procura() {
    setProcurando(true);
    setErro("");
    try {
      const resposta = await api.descobreNoCanal("chatwoot", { url, token_admin: token });
      setAchado(resposta);
      const primeira = resposta.contas?.[0];
      if (primeira) setConta(String(primeira.id));
    } catch (problema) {
      setErro(mensagem(problema));
    } finally {
      setProcurando(false);
    }
  }

  return (
    <div>
      <p className="text-sm text-muted">
        O token de administrador fica guardado cifrado e serve para todos os agentes deste Chatwoot.
      </p>
      <div className="mt-4 grid gap-4 sm:grid-cols-2">
        <Campo
          rotulo="Endereço do Chatwoot"
          placeholder="https://chat.suaempresa.com.br"
          value={url}
          onChange={(e) => setUrl(e.target.value)}
        />
        <Campo
          rotulo="Token de administrador"
          type="password"
          value={token}
          onChange={(e) => setToken(e.target.value)}
        />
      </div>

      <div className="mt-4">
        <Botao
          pequeno
          icone="sys-search"
          ocupado={procurando}
          disabled={!url.trim() || !token.trim()}
          onClick={procura}
        >
          Procurar as caixas
        </Botao>
      </div>

      {erro && (
        <div className="mt-4">
          <Aviso tom="erro" titulo="o Chatwoot não respondeu">
            {erro}
          </Aviso>
        </div>
      )}

      {achado?.contas && achado.contas.length > 0 && (
        <div className="mt-6">
          <label className="block">
            <span className="rotulo">Conta</span>
            <select
              value={conta}
              onChange={(e) => {
                setConta(e.target.value);
                setCaixas([]);
              }}
              className="mt-2 w-full rounded-md border border-borda bg-surface px-3 py-2 text-sm text-texto focus:border-ciano focus:outline-none"
            >
              {achado.contas.map((c) => (
                <option key={c.id} value={String(c.id)}>
                  {c.nome || `conta ${c.id}`}
                </option>
              ))}
            </select>
          </label>

          <p className="rotulo mt-6">Caixas em que ele atende</p>
          <ul className="mt-2 flex flex-col gap-1">
            {(daConta?.caixas ?? []).map((caixa) => (
              <li key={caixa.id}>
                <label className="flex cursor-pointer items-center gap-3 rounded-md border border-borda px-3 py-2 text-sm text-texto">
                  <input
                    type="checkbox"
                    className="accent-ciano"
                    checked={caixas.includes(caixa.id)}
                    onChange={(e) =>
                      setCaixas((antes) =>
                        e.target.checked
                          ? [...antes, caixa.id]
                          : antes.filter((i) => i !== caixa.id),
                      )
                    }
                  />
                  <span className="min-w-0 flex-1 truncate">{caixa.nome || `caixa ${caixa.id}`}</span>
                  {caixa.tipo && <span className="text-xs text-dim">{caixa.tipo}</span>}
                </label>
              </li>
            ))}
          </ul>
          {(daConta?.caixas ?? []).length === 0 && (
            <p className="mt-2 text-sm text-dim">Esta conta não tem caixa nenhuma.</p>
          )}

          <Conectar
            rotulo="Ligar ao Chatwoot"
            desligado={caixas.length === 0}
            ajuda="Ele cria o bot na conta e liga nas caixas marcadas."
            aoConectar={async () => {
              atualiza(
                await api.conectaCanal(agente.id, {
                  canal: "chatwoot",
                  conexao: {
                    url,
                    token_admin: token,
                    account_id: Number(conta),
                    inbox_ids: caixas,
                  },
                }),
              );
            }}
          />
        </div>
      )}
    </div>
  );
}

function Waha({ agente, atualiza }: { agente: Agente; atualiza: (a: Agente) => void }) {
  return (
    <div>
      <p className="text-sm text-muted">
        Ele cria uma sessão e mostra o QR code para você ler no celular. É a API não oficial: a Meta
        pode bloquear o número sem aviso, então use um chip só do agente.
      </p>
      <p className="mt-3 text-sm text-dim">
        O WhatsApp pelo aparelho roda num contêiner que sobe sob demanda. Se esta instalação nunca
        teve um agente assim, ligue o primeiro pelo terminal (<span className="tecnico">asimov</span>{" "}
        e depois criar agente): subir contêiner é coisa da VPS, não do navegador.
      </p>

      <Conectar
        rotulo="Criar a sessão"
        ajuda="Depois de criar, o QR code aparece nesta mesma aba."
        aoConectar={async () => {
          atualiza(await api.conectaCanal(agente.id, { canal: "waha", conexao: {} }));
        }}
      />
    </div>
  );
}

function WhatsApp({ agente, atualiza }: { agente: Agente; atualiza: (a: Agente) => void }) {
  const [app, setApp] = useState("");
  const [token, setToken] = useState("");
  const [segredo, setSegredo] = useState("");
  const [contas, setContas] = useState<{ id: string; nome?: string | null }[] | null>(null);
  const [conta, setConta] = useState("");
  const [achado, setAchado] = useState<DescobertaNoCanal | null>(null);
  const [numero, setNumero] = useState("");
  const [procurando, setProcurando] = useState(false);
  const [erro, setErro] = useState("");

  async function procuraContas() {
    setProcurando(true);
    setErro("");
    try {
      const resposta = await api.descobreNoCanal("whatsapp", {
        app_id: app,
        access_token: token,
        app_secret: segredo,
      });
      const achadas = (resposta.contas ?? []).map((c) => ({
        id: String(c.id),
        nome: c.nome,
      }));
      setContas(achadas);
      if (achadas.length === 1) await escolheConta(achadas[0].id);
    } catch (problema) {
      setErro(mensagem(problema));
    } finally {
      setProcurando(false);
    }
  }

  async function escolheConta(id: string) {
    setConta(id);
    setAchado(null);
    setNumero("");
    setErro("");
    try {
      setAchado(
        await api.descobreNoCanal("whatsapp", { access_token: token, waba_id: id }),
      );
    } catch (problema) {
      setErro(mensagem(problema));
    }
  }

  return (
    <div>
      <p className="text-sm text-muted">
        Do app da Meta: o ID, o token permanente e a chave secreta. Eles ficam guardados cifrados e
        nunca voltam para o navegador. A Meta cobra por mensagem, com mil grátis por número por mês.
      </p>
      <div className="mt-4 grid gap-4 sm:grid-cols-3">
        <Campo rotulo="ID do app" value={app} onChange={(e) => setApp(e.target.value)} />
        <Campo
          rotulo="Token permanente"
          type="password"
          value={token}
          onChange={(e) => setToken(e.target.value)}
        />
        <Campo
          rotulo="Chave secreta do app"
          type="password"
          value={segredo}
          onChange={(e) => setSegredo(e.target.value)}
        />
      </div>

      <div className="mt-4">
        <Botao
          pequeno
          icone="sys-search"
          ocupado={procurando}
          disabled={!app.trim() || !token.trim() || !segredo.trim()}
          onClick={procuraContas}
        >
          Procurar as contas do token
        </Botao>
      </div>

      {erro && (
        <div className="mt-4">
          <Aviso tom="erro" titulo="a Meta não respondeu">
            {erro}
          </Aviso>
        </div>
      )}

      {contas && contas.length > 1 && (
        <label className="mt-6 block">
          <span className="rotulo">Conta de WhatsApp Business</span>
          <select
            value={conta}
            onChange={(e) => void escolheConta(e.target.value)}
            className="mt-2 w-full rounded-md border border-borda bg-surface px-3 py-2 text-sm text-texto focus:border-ciano focus:outline-none"
          >
            <option value="">escolha a conta</option>
            {contas.map((c) => (
              <option key={c.id} value={c.id}>
                {c.nome || c.id}
              </option>
            ))}
          </select>
        </label>
      )}

      {contas && contas.length === 0 && (
        <div className="mt-4">
          <Aviso tom="atencao" titulo="o token não enxerga nenhuma conta">
            Isso costuma ser token gerado antes de a conta ser atribuída ao usuário do sistema. Gere
            o token de novo e tente outra vez.
          </Aviso>
        </div>
      )}

      {achado?.numeros && (
        <div className="mt-6">
          <p className="rotulo">Número do agente</p>
          <ul className="mt-2 flex flex-col gap-1">
            {achado.numeros.map((n) => (
              <li key={n.id}>
                <button
                  onClick={() => setNumero(n.id)}
                  aria-pressed={numero === n.id}
                  className={`flex w-full items-center gap-3 rounded-md border px-3 py-2 text-left text-sm transition-colors ${
                    numero === n.id
                      ? "border-ciano bg-ciano/5 text-texto"
                      : "border-borda text-muted hover:text-texto"
                  }`}
                >
                  <span className="tecnico">{n.numero}</span>
                  {n.nome && <span className="truncate text-xs text-dim">{n.nome}</span>}
                </button>
              </li>
            ))}
          </ul>
          {achado.numeros.length === 0 && (
            <p className="mt-2 text-sm text-dim">Esta conta não tem número nenhum.</p>
          )}

          <Conectar
            rotulo="Ligar ao WhatsApp"
            desligado={!numero}
            ajuda="Ele aponta o webhook deste número para o endereço do agente."
            aoConectar={async () => {
              atualiza(
                await api.conectaCanal(agente.id, {
                  canal: "whatsapp",
                  conexao: {
                    app_id: app,
                    access_token: token,
                    app_secret: segredo,
                    waba_id: conta,
                    phone_number_id: numero,
                  },
                }),
              );
            }}
          />
        </div>
      )}
    </div>
  );
}
