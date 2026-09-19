import { useCallback, useEffect, useState } from "react";
import { useNavigate } from "react-router-dom";
import {
  api,
  ErroDaApi,
  SemSessao,
  type CanalDisponivel,
  type LinhaDeCanal,
} from "../api/cliente";
import { Busca } from "../design/Busca";
import { Aviso } from "../design/Aviso";
import { Botao } from "../design/Botao";
import { Cabecalho } from "../design/Cabecalho";
import { Carregando } from "../design/Carregando";
import { Dica } from "../design/Dica";
import { Marca } from "../design/Marca";
import { Modal } from "../design/Modal";
import { Vazio } from "../design/Vazio";
import { CANAIS, ROTULO_DO_CANAL } from "./agente/canais";

/** A tela de Canais, em duas partes.
 *
 *  **As integrações**: o que esta instalação sabe conectar, o que cada uma exige antes de começar e
 *  quantos agentes já atendem por ela. Faltava: a tela só mostrava quem já tinha canal, e quem
 *  abria sem nenhum agente não descobria por aqui o que dava para conectar.
 *
 *  **Quem está atendendo**: uma linha por agente com a resposta do canal agora. Cada canal é
 *  perguntado em separado, e o que não responder vira linha vermelha em vez de derrubar a tela.
 */

/** A cor da situação vira uma barra por dentro do cartão, nunca a borda de um lado: borda mais
 *  grossa de um lado só com canto arredondado faz o canto virar uma cunha. */
const COR: Record<string, string> = {
  ok: "bg-ok",
  atencao: "bg-atencao",
  perigo: "bg-perigo",
  neutro: "bg-dim",
};

export function Canais() {
  const [linhas, setLinhas] = useState<LinhaDeCanal[] | null>(null);
  const [disponiveis, setDisponiveis] = useState<CanalDisponivel[]>([]);
  const [erro, setErro] = useState("");
  const [qr, setQr] = useState<{ agente: string; texto: string | null } | null>(null);
  const [ocupado, setOcupado] = useState("");
  const [filtro, setFiltro] = useState("");

  const busca = useCallback(() => {
    setErro("");
    api
      .situacaoDosCanais()
      .then(setLinhas)
      .catch((problema) => {
        if (problema instanceof SemSessao) throw problema;
        setErro(problema.message);
      });
  }, []);

  useEffect(busca, [busca]);

  const procurado = filtro.trim().toLowerCase();
  const achadas = (linhas ?? []).filter(
    (l) =>
      !procurado ||
      l.agente.toLowerCase().includes(procurado) ||
      l.empresa.toLowerCase().includes(procurado),
  );

  // O catálogo é o que a instalação sabe conectar.
  useEffect(() => {
    api.canais().then(setDisponiveis).catch(() => setDisponiveis([]));
  }, []);

  const navega = useNavigate();

  async function reinicia(linha: LinhaDeCanal) {
    setOcupado(linha.agente_id);
    try {
      await api.acaoNoCanal(linha.agente_id, "reiniciar");
      busca();
      await mostraQr(linha);
    } catch (problema) {
      setErro(problema instanceof ErroDaApi ? problema.message : String(problema));
    } finally {
      setOcupado("");
    }
  }

  async function mostraQr(linha: LinhaDeCanal) {
    setQr({ agente: linha.agente, texto: null });
    try {
      const resposta = await api.acaoNoCanal(linha.agente_id, "qr");
      setQr({ agente: linha.agente, texto: resposta.qr ?? null });
    } catch {
      setQr({ agente: linha.agente, texto: null });
    }
  }

  return (
    <>
      <Cabecalho
        titulo="Canais"
        contexto="Por onde cada agente atende, e se está respondendo agora."
        acoes={
          <>
          <Busca
            valor={filtro}
            aoMudar={setFiltro}
            rotulo="Buscar canal"
            placeholder="agente ou empresa"
          />
          <Botao className="min-h-11" icone="sys-refresh" onClick={busca}>
            Conferir de novo
          </Botao>
          </>
        }
      />

      {disponiveis.length > 0 && (
        <section className="mt-8">
          <h2 className="rotulo">Integrações desta instalação</h2>
          <ul className="mt-3 grid gap-3 md:grid-cols-2 xl:grid-cols-4">
            {disponiveis.map((c) => {
              const texto = CANAIS[c.nome];
              const quantos = (linhas ?? []).filter((l) => l.canal === c.nome).length;
              return (
                <li
                  key={c.nome}
                  className="flex flex-col gap-2 rounded-lg border border-borda bg-surface p-4"
                >
                  <span className="flex items-start gap-2.5">
                    <span className="flex h-9 w-9 shrink-0 items-center justify-center rounded-md border border-borda text-muted">
                      {texto && <Marca nome={texto.marca} tamanho={18} />}
                    </span>
                    <span className="min-w-0 flex-1 text-sm font-medium leading-snug text-texto">
                      {ROTULO_DO_CANAL(c.nome)}
                    </span>
                    {/* O aviso é só o ícone, e o texto abre no hover e no foco: aberto, ele ocupava
                        mais linha que a descrição do canal. */}
                    {texto?.atencao && <Dica texto={texto.atencao} />}
                  </span>

                  <p className="text-sm leading-snug text-muted">{texto?.serve}</p>
                  <p className="text-xs leading-snug text-dim">Precisa: {texto?.exige ?? "nada"}</p>

                  <div className="mt-auto flex flex-wrap items-center justify-between gap-2 pt-2">
                    <span className="text-xs text-dim">
                      {quantos === 0 ? "nenhum agente" : quantos === 1 ? "1 agente" : `${quantos} agentes`}
                    </span>
                    <Botao pequeno icone="act-add" onClick={() => navega("/agentes/novo")}>
                      Criar agente
                    </Botao>
                  </div>
                </li>
              );
            })}
          </ul>
        </section>
      )}

      <h2 className="rotulo mt-10">Quem está atendendo</h2>

      {erro ? (
        <div className="mt-3">
          <Aviso tom="erro" titulo="não deu para carregar os canais">
            <p>{erro}</p>
            <div className="mt-4">
              <Botao icone="sys-refresh" pequeno onClick={busca}>
                Tentar de novo
              </Botao>
            </div>
          </Aviso>
        </div>
      ) : linhas === null ? (
        <div className="mt-16">
          <Carregando tipo="pulso" o_que="perguntando a cada canal" />
        </div>
      ) : achadas.length === 0 ? (
        <div className="mt-10">
          {procurado ? (
            <Vazio titulo="nenhum canal com esse nome" icone="sys-search" />
          ) : (
            <Vazio titulo="nenhum agente atendendo ainda" icone="cont-link">
              Escolha uma integração acima para criar o primeiro.
            </Vazio>
          )}
        </div>
      ) : (
        <ul className="mt-3 flex flex-col gap-3">
          {achadas.map((l) => {
            const marca = CANAIS[l.canal]?.marca;
            return (
              <li
                key={l.agente_id}
                className="relative flex flex-wrap items-center justify-between gap-4 rounded-lg border border-borda bg-surface p-5 pl-6"
              >
                <span
                  aria-hidden="true"
                  className={`absolute inset-y-4 left-2.5 w-0.5 rounded-full ${COR[l.situacao.cor] ?? COR.neutro}`}
                />
                <div className="min-w-0 basis-56">
                  <p className="truncate text-base text-texto">
                    {l.agente}
                    <span className="text-muted">, em {l.empresa}</span>
                  </p>
                  <p className="mt-0.5 flex items-center gap-1.5 text-sm text-muted">
                    {marca && <Marca nome={marca} tamanho={14} />}
                    <span className="truncate">
                      {ROTULO_DO_CANAL(l.canal)}
                      {l.situacao_do_agente === "treinamento" && " (agente em treinamento)"}
                      {l.situacao_do_agente === "inativo" && " (agente desativado)"}
                    </span>
                  </p>
                </div>

                <div className="min-w-0 flex-1">
                  <p className="text-sm text-texto">{l.situacao.resumo}</p>
                  {l.situacao.erro && <p className="tecnico mt-1 break-words text-dim">{l.situacao.erro}</p>}
                </div>

                {l.canal === "waha" && (
                  <div className="flex shrink-0 flex-wrap gap-2">
                    <Botao pequeno icone="sys-fullscreen" onClick={() => mostraQr(l)}>
                      Ver QR code
                    </Botao>
                    <Botao
                      pequeno
                      icone="sys-refresh"
                      ocupado={ocupado === l.agente_id}
                      onClick={() => reinicia(l)}
                    >
                      Reconectar
                    </Botao>
                  </div>
                )}
              </li>
            );
          })}
        </ul>
      )}

      {qr && (
        <Modal
          titulo={`Conectar o número de ${qr.agente}`}
          subtitulo="Abra o WhatsApp no celular, vá em Aparelhos conectados e aponte a câmera."
          aoFechar={() => setQr(null)}
          largura="max-w-xl"
          altura="conteudo"
        >
          {qr.texto === null ? (
            <div className="py-8">
              <Carregando tipo="pulso" o_que="esperando o QR code" />
              <p className="mt-4 text-center text-sm text-muted">
                Se ele não aparecer, use Reconectar para gerar um novo.
              </p>
            </div>
          ) : (
            <div className="flex flex-col items-center gap-4">
              <img
                src={`data:image/png;base64,${qr.texto}`}
                alt="QR code para conectar o número"
                className="w-full max-w-xs rounded-lg border border-borda bg-white p-2"
              />
              <p className="text-sm text-muted">
                O código expira em poucos segundos. Use Reconectar para gerar um novo.
              </p>
            </div>
          )}
        </Modal>
      )}
    </>
  );
}
