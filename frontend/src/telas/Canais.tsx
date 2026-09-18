import { useCallback, useEffect, useState } from "react";
import { api, ErroDaApi, SemSessao, type Empresa, type LinhaDeCanal } from "../api/cliente";
import { Aviso } from "../design/Aviso";
import { Botao } from "../design/Botao";
import { Carregando } from "../design/Carregando";
import { Modal } from "../design/Modal";
import { Vazio } from "../design/Vazio";
import { ROTULO_DO_CANAL } from "./agente/canais";

/** A tela de Canais: uma linha por agente com a resposta do canal agora.
 *
 *  Cada canal é perguntado em separado no backend, e o que não responder vira linha vermelha em vez
 *  de derrubar a tela. Criar canal continua no terminal nesta versão; aqui dá para conferir,
 *  reiniciar a sessão do WhatsApp e ler o QR code de novo.
 */

const COR: Record<string, string> = {
  ok: "border-l-ok",
  atencao: "border-l-atencao",
  perigo: "border-l-perigo",
  neutro: "border-l-dim",
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
      <header className="flex flex-wrap items-end justify-between gap-6 border-b border-borda pb-6">
        <div>
          <h1 className="text-3xl font-semibold tracking-tight text-texto md:text-5xl">
            Canais<span className="text-lime">.</span>
          </h1>
          <p className="mt-2 text-sm text-muted">Por onde cada agente atende, e se está de pé agora.</p>
        </div>

        <div className="flex flex-wrap items-center gap-3">
          {empresas.length > 1 && (
            <select
              value={empresa}
              aria-label="Empresa"
              onChange={(e) => aoTrocarEmpresa(e.target.value)}
              className="border border-borda bg-surface px-4 py-2 font-mono text-xs uppercase tracking-[0.15em] text-muted transition-colors hover:text-texto focus:border-lime"
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
        </div>
      </header>

      {erro ? (
        <div className="mt-10">
          <Aviso tom="erro" titulo="a consulta não voltou">
            {erro}
          </Aviso>
        </div>
      ) : linhas === null ? (
        <div className="mt-16">
          <Carregando tipo="pulso" o_que="perguntando a cada canal" />
        </div>
      ) : linhas.length === 0 ? (
        <div className="mt-16">
          <Vazio titulo="nenhum agente ainda" icone="cont-link">
            Canal é do agente: crie um agente para ter o que conferir aqui.
          </Vazio>
        </div>
      ) : (
        <ul className="mt-10 flex flex-col gap-3">
          {linhas.map((l) => (
            <li
              key={l.agente_id}
              className={`flex flex-wrap items-center justify-between gap-4 border border-borda border-l-2 bg-surface p-5 ${COR[l.situacao.cor] ?? COR.neutro}`}
            >
              <div className="min-w-0">
                <p className="text-base text-texto">
                  {l.agente}
                  {!empresa && <span className="text-muted">, em {l.empresa}</span>}
                </p>
                <p className="mt-0.5 text-sm text-muted">
                  {ROTULO_DO_CANAL(l.canal)}
                  {!l.ativo && " (agente desligado)"}
                </p>
                <p className="mt-2 text-sm text-texto">{l.situacao.resumo}</p>
                {l.situacao.erro && (
                  <p className="mt-1 font-mono text-xs text-dim">{l.situacao.erro}</p>
                )}
              </div>

              {l.canal === "waha" && (
                <div className="flex flex-wrap gap-2">
                  <Botao pequeno icone="sys-fullscreen" onClick={() => mostraQr(l)}>
                    Ver QR code
                  </Botao>
                  <Botao
                    pequeno
                    icone="sys-refresh"
                    ocupado={ocupado === l.agente_id}
                    onClick={() => reinicia(l)}
                  >
                    Reiniciar
                  </Botao>
                </div>
              )}
            </li>
          ))}
        </ul>
      )}

      {qr && (
        <Modal
          titulo={`Parear o número de ${qr.agente}`}
          subtitulo="Abra o WhatsApp no celular, vá em Aparelhos conectados e aponte a câmera."
          aoFechar={() => setQr(null)}
          largura="max-w-xl"
        >
          {qr.texto === null ? (
            <div className="py-8">
              <Carregando tipo="pulso" o_que="esperando o QR code" />
              <p className="mt-4 text-center text-sm text-muted">
                O QR code só existe enquanto a sessão espera a leitura. Se não aparecer, reinicie a
                sessão para vir um novo.
              </p>
            </div>
          ) : (
            <div className="flex flex-col items-center gap-4">
              <img
                src={`data:image/png;base64,${qr.texto}`}
                alt="QR code para parear o número"
                className="w-full max-w-xs border border-borda bg-white p-2"
              />
              <p className="text-sm text-muted">
                O código expira em poucos segundos. Reinicie a sessão se ele vencer.
              </p>
            </div>
          )}
        </Modal>
      )}
    </>
  );
}
