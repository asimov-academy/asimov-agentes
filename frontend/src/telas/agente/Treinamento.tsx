import { useCallback, useEffect, useRef, useState } from "react";
import { api, ErroDaApi, type Agente, type MaterialDaBase } from "../../api/cliente";
import { Aviso } from "../../design/Aviso";
import { Botao } from "../../design/Botao";
import { Campo } from "../../design/Campo";
import { Carregando } from "../../design/Carregando";
import { Icone } from "../../design/Icone";
import { Selo } from "../../design/Selo";
import type { ICONES } from "../../design/icones";

/** O treinamento do agente: o que ele sabe, além do prompt.
 *
 *  Cada aba é uma forma de ensinar a mesma coisa, e todas terminam no mesmo lugar: trechos que o
 *  agente busca na hora de responder. Texto, site e documento funcionam; vídeo e base compartilhada
 *  entre agentes continuam desenhados, porque o lugar combinado veio antes da máquina.
 *
 *  A lista embaixo é a base do agente. Material entra como "processando" e vira "pronto" quando o
 *  worker termina de gerar os vetores, então a tela relê enquanto houver algo em andamento.
 */
type Fonte = {
  chave: "texto" | "site" | "documento" | "video" | "base";
  rotulo: string;
  icone: keyof typeof ICONES;
  titulo: string;
  explica: string;
  exemplo: string;
  pronta: boolean;
};

const FONTES: Fonte[] = [
  {
    chave: "texto",
    rotulo: "Texto",
    icone: "comm-comment",
    titulo: "Ensinar por frase",
    explica:
      "Uma afirmação por vez, do jeito que você diria para alguém novo na equipe. É o caminho mais curto para corrigir uma resposta errada.",
    exemplo: "Ex: não trabalhamos com entrega fora do estado.",
    pronta: true,
  },
  {
    chave: "site",
    rotulo: "Site",
    icone: "cont-link",
    titulo: "Ensinar por site",
    explica:
      "O endereço de uma página. A plataforma lê o texto dela agora; se a página mudar, envie de novo.",
    exemplo: "Ex: https://suaempresa.com.br/produtos",
    pronta: true,
  },
  {
    chave: "documento",
    rotulo: "Documento",
    icone: "cont-doc",
    titulo: "Ensinar por documento",
    explica:
      "Tabela de preço, catálogo, manual, política de troca. PDF, DOCX, TXT ou MD, com o texto dividido em trechos.",
    exemplo: "Ex: tabela-de-precos.pdf",
    pronta: true,
  },
  {
    chave: "video",
    rotulo: "Vídeo",
    icone: "cont-video",
    titulo: "Ensinar por vídeo",
    explica:
      "Um vídeo em que alguém já explicou o que o agente precisa saber. Vale a fala, transcrita.",
    exemplo: "Ex: o vídeo de apresentação do produto",
    pronta: false,
  },
  {
    chave: "base",
    rotulo: "Base compartilhada",
    icone: "nav-projects",
    titulo: "Conectar uma base",
    explica:
      "Uma base que já existe, montada uma vez e ligada em quantos agentes precisar. Muda num lugar e vale em todos.",
    exemplo: "Ex: a base da Loja Sul, usada por três agentes",
    pronta: false,
  },
];

const ROTULO_DA_ORIGEM: Record<string, string> = {
  texto: "Texto",
  site: "Site",
  documento: "Documento",
};

const RELE_EM_MS = 3000;

function mensagem(problema: unknown): string {
  return problema instanceof ErroDaApi ? problema.message : String(problema);
}

export function Treinamento({ agente }: { agente: Agente }) {
  const [fonte, setFonte] = useState<Fonte>(FONTES[0]);
  const [materiais, setMateriais] = useState<MaterialDaBase[] | null>(null);
  const [modelo, setModelo] = useState("");
  const [erro, setErro] = useState("");

  const busca = useCallback(async () => {
    try {
      const base = await api.documentos(agente.id);
      setMateriais(base.documentos);
      setModelo(base.modelo_embeddings);
    } catch (problema) {
      setErro(mensagem(problema));
    }
  }, [agente.id]);

  useEffect(() => {
    void busca();
  }, [busca]);

  // Enquanto houver material em andamento, a tela pergunta de novo: quem termina é o worker.
  const emAndamento = (materiais ?? []).some((m) => m.status === "processando");
  useEffect(() => {
    if (!emAndamento) return;
    const relogio = setInterval(() => void busca(), RELE_EM_MS);
    return () => clearInterval(relogio);
  }, [emAndamento, busca]);

  return (
    <div className="flex flex-col gap-6">
      <div className="flex flex-wrap items-center gap-x-2 gap-y-1 border-b border-borda">
        {FONTES.map((f) => (
          <button
            key={f.chave}
            onClick={() => setFonte(f)}
            aria-pressed={fonte.chave === f.chave}
            className={`-mb-px border-b-2 px-3 py-2 text-sm transition-colors ${
              fonte.chave === f.chave
                ? "border-ciano text-ciano"
                : "border-transparent text-muted hover:text-texto"
            }`}
          >
            {f.rotulo}
          </button>
        ))}
      </div>

      {modelo === "" && (
        <Aviso tom="atencao" titulo="falta a chave de uma IA que gere vetores">
          O material só vira busca com a chave da OpenAI ou do Gemini nesta instalação. Guarde uma na
          aba Configurações deste agente e envie o material de novo.
        </Aviso>
      )}

      <section className="relative rounded-lg border border-borda bg-panel p-6">
        {!fonte.pronta && (
          <span className="absolute right-4 top-4 rounded-full border border-borda px-2 py-0.5 text-[0.5625rem] uppercase tracking-[0.06em] text-dim">
            em breve
          </span>
        )}
        <div className="flex items-start gap-4">
          <span className="flex h-10 w-10 shrink-0 items-center justify-center rounded-md border border-borda text-ciano">
            <Icone nome={fonte.icone} tamanho={18} />
          </span>
          <div className="min-w-0 flex-1">
            <h4 className="text-base font-semibold text-texto">{fonte.titulo}</h4>
            <p className="mt-1 text-sm leading-relaxed text-muted">{fonte.explica}</p>
            {fonte.pronta ? (
              <div className="mt-4">
                {fonte.chave === "texto" && <PorTexto agente={agente} aoEnviar={busca} />}
                {fonte.chave === "site" && <PorSite agente={agente} aoEnviar={busca} />}
                {fonte.chave === "documento" && <PorArquivo agente={agente} aoEnviar={busca} />}
              </div>
            ) : (
              <p className="mt-3 font-mono text-xs text-dim">{fonte.exemplo}</p>
            )}
          </div>
        </div>
      </section>

      <section>
        <p className="rotulo">O que {agente.nome} já sabe</p>
        {erro && (
          <div className="mt-2">
            <Aviso tom="erro" titulo="não deu para ler a base">
              {erro}
            </Aviso>
          </div>
        )}
        {materiais === null ? (
          <div className="mt-3">
            <Carregando tipo="pontos" o_que="lendo a base" />
          </div>
        ) : materiais.length === 0 ? (
          <p className="mt-2 text-sm text-dim">
            Nada ainda. O que ele sabe vem do prompt, na aba Trabalho, e do que ele busca na web
            quando a ferramenta está ligada.
          </p>
        ) : (
          <ul className="mt-3 flex flex-col gap-2">
            {materiais.map((material) => (
              <Material
                key={material.id}
                agente={agente}
                material={material}
                aoRemover={busca}
              />
            ))}
          </ul>
        )}
      </section>
    </div>
  );
}

function Material({
  agente,
  material,
  aoRemover,
}: {
  agente: Agente;
  material: MaterialDaBase;
  aoRemover: () => Promise<void>;
}) {
  const [removendo, setRemovendo] = useState(false);

  return (
    <li className="flex flex-wrap items-center gap-3 rounded-md border border-borda px-4 py-3">
      <span className="min-w-0 flex-1">
        <span className="block truncate text-sm text-texto">{material.nome}</span>
        <span className="mt-0.5 block text-xs text-dim">
          {ROTULO_DA_ORIGEM[material.origem] ?? material.origem}
          {material.status === "pronto" &&
            ` · ${material.total_trechos} ${material.total_trechos === 1 ? "trecho" : "trechos"}`}
          {material.status === "erro" && material.erro && ` · ${material.erro}`}
        </span>
      </span>
      {material.status === "pronto" && <Selo tom="ok">pronto</Selo>}
      {material.status === "processando" && <Selo>processando</Selo>}
      {material.status === "erro" && <Selo tom="perigo">erro</Selo>}
      <Botao
        pequeno
        icone="act-delete"
        ocupado={removendo}
        onClick={async () => {
          setRemovendo(true);
          try {
            await api.removeDocumento(agente.id, material.id);
            await aoRemover();
          } finally {
            setRemovendo(false);
          }
        }}
      >
        Remover
      </Botao>
    </li>
  );
}

/** O formulário de cada forma de ensinar, com o erro logo abaixo do botão que o causou. */
function Envio({
  rotulo,
  desligado,
  children,
  aoEnviar,
}: {
  rotulo: string;
  desligado: boolean;
  children: React.ReactNode;
  aoEnviar: () => Promise<void>;
}) {
  const [ocupado, setOcupado] = useState(false);
  const [erro, setErro] = useState("");

  return (
    <div>
      {children}
      {erro && (
        <div className="mt-3">
          <Aviso tom="erro" titulo="não deu para ensinar isso">
            {erro}
          </Aviso>
        </div>
      )}
      <div className="mt-3">
        <Botao
          tom="solido"
          pequeno
          icone="act-upload"
          ocupado={ocupado}
          disabled={desligado}
          onClick={async () => {
            setOcupado(true);
            setErro("");
            try {
              await aoEnviar();
            } catch (problema) {
              setErro(mensagem(problema));
            } finally {
              setOcupado(false);
            }
          }}
        >
          {rotulo}
        </Botao>
      </div>
    </div>
  );
}

function PorTexto({ agente, aoEnviar }: { agente: Agente; aoEnviar: () => Promise<void> }) {
  const [texto, setTexto] = useState("");

  return (
    <Envio
      rotulo="Ensinar"
      desligado={texto.trim().length < 3}
      aoEnviar={async () => {
        await api.enviaTexto(agente.id, texto.trim());
        setTexto("");
        await aoEnviar();
      }}
    >
      <textarea
        value={texto}
        onChange={(e) => setTexto(e.target.value)}
        rows={3}
        placeholder="Não trabalhamos com entrega fora do estado."
        aria-label="o que o agente precisa saber"
        className="w-full resize-y rounded-md border border-borda bg-surface p-3 text-sm text-texto placeholder:text-dim focus:border-ciano focus:outline-none"
      />
    </Envio>
  );
}

function PorSite({ agente, aoEnviar }: { agente: Agente; aoEnviar: () => Promise<void> }) {
  const [url, setUrl] = useState("");

  return (
    <Envio
      rotulo="Ler a página"
      desligado={!url.trim().startsWith("http")}
      aoEnviar={async () => {
        await api.enviaSite(agente.id, url.trim());
        setUrl("");
        await aoEnviar();
      }}
    >
      <Campo
        rotulo="Endereço da página"
        placeholder="https://suaempresa.com.br/produtos"
        value={url}
        onChange={(e) => setUrl(e.target.value)}
      />
    </Envio>
  );
}

function PorArquivo({ agente, aoEnviar }: { agente: Agente; aoEnviar: () => Promise<void> }) {
  const [arquivo, setArquivo] = useState<File | null>(null);
  const campo = useRef<HTMLInputElement>(null);

  return (
    <Envio
      rotulo="Enviar o arquivo"
      desligado={arquivo === null}
      aoEnviar={async () => {
        if (arquivo) await api.enviaDocumento(agente.id, arquivo);
        setArquivo(null);
        if (campo.current) campo.current.value = "";
        await aoEnviar();
      }}
    >
      <input
        ref={campo}
        type="file"
        accept=".pdf,.docx,.txt,.md"
        aria-label="arquivo para ensinar"
        onChange={(e) => setArquivo(e.target.files?.[0] ?? null)}
        className="block w-full text-sm text-muted file:mr-3 file:rounded-md file:border file:border-borda file:bg-surface file:px-3 file:py-2 file:text-sm file:text-texto hover:file:border-ciano"
      />
    </Envio>
  );
}
