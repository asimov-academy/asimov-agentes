import { useCallback, useEffect, useState } from "react";
import { api, ErroDaApi, SemSessao, type Empresa, type LinhaDeCanal } from "../api/cliente";
import { Aviso } from "../design/Aviso";
import { Botao } from "../design/Botao";
import { Cabecalho } from "../design/Cabecalho";
import { Carregando } from "../design/Carregando";
import { Marca } from "../design/Marca";
import { Modal } from "../design/Modal";
import { Vazio } from "../design/Vazio";
import { CANAIS, ROTULO_DO_CANAL } from "./agente/canais";

/** A tela de Canais: uma linha por agente com a resposta do canal agora.
 *
 *  Cada canal é perguntado em separado, e o que não responder vira linha vermelha em vez de
 *  derrubar a tela. Criar canal continua no terminal nesta versão; aqui dá para conferir,
 *  reconectar o WhatsApp e ler o QR code de novo.
 */

/** A cor da situação vira uma barra por dentro do cartão, nunca a borda de um lado: borda mais
 *  grossa de um lado só com canto arredondado faz o canto virar uma cunha. */
const COR: Record<string, string> = {
  ok: "bg-ok",
  atencao: "bg-atencao",
  perigo: "bg-perigo",
  neutro: "bg-dim",
};

export function Canais({
  empresas,
  empresa,
  aoTrocarEmpresa,
}: {
  empresas: Empresa[];
  empresa: string;
  aoTrocarEmpresa: (id: string) => void;
}) {
  const [linhas, setLinhas] = useState<LinhaDeCanal[] | null>(null);
  const [erro, setErro] = useState("");
  const [qr, setQr] = useState<{ agente: string; texto: string | null } | null>(null);
  const [ocupado, setOcupado] = useState("");

  const busca = useCallback(() => {
    setErro("");
    api
      .situacaoDosCanais(empresa || undefined)
      .then(setLinhas)
      .catch((problema) => {
        if (problema instanceof SemSessao) throw problema;
        setErro(problema.message);
      });
  }, [empresa]);

  useEffect(busca, [busca]);

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
          {empresas.length > 1 && (
            <select
              value={empresa}
              aria-label="Empresa"
              onChange={(e) => aoTrocarEmpresa(e.target.value)}
              className="rounded-md border border-borda bg-surface px-3 py-2 text-sm text-muted transition-colors hover:text-texto focus:border-ciano focus:outline-none"
            >
              <option value="">Todas as empresas</option>
              {empresas.map((e) => (
                <option key={e.id} value={e.id}>
                  {e.nome}
                </option>
              ))}
            </select>
          )}
          <Botao pequeno icone="sys-refresh" onClick={busca}>
            Conferir de novo
          </Botao>
          </>
        }
      />

      {erro ? (
        <div className="mt-10">
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
      ) : linhas.length === 0 ? (
        <div className="mt-16">
          <Vazio titulo="nenhum agente ainda" icone="cont-link">
            Crie um agente para ter o que conferir aqui.
          </Vazio>
        </div>
      ) : (
        <ul className="mt-10 flex flex-col gap-3">
          {linhas.map((l) => {
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
                    {!empresa && <span className="text-muted">, em {l.empresa}</span>}
                  </p>
                  <p className="mt-0.5 flex items-center gap-1.5 text-sm text-muted">
                    {marca && <Marca nome={marca} tamanho={14} />}
                    <span className="truncate">
                      {ROTULO_DO_CANAL(l.canal)}
                      {!l.ativo && " (agente inativo)"}
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
