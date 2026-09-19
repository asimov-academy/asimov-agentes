import { useState } from "react";
import { api, type CasoDaProva } from "../../api/cliente";
import { Botao } from "../../design/Botao";
import { Aviso } from "../../design/Aviso";

export function Prova({ agenteId, pendente }: { agenteId: string; pendente: boolean }) {
  const [casos, setCasos] = useState<CasoDaProva[]>([]);
  const [anteriores, setAnteriores] = useState<CasoDaProva[]>([]);
  const [rodando, setRodando] = useState(false);
  const [erro, setErro] = useState("");
  async function roda() {
    setRodando(true);
    setErro("");
    try {
      const resposta = await api.prova(agenteId);
      setAnteriores(casos);
      setCasos(resposta.casos);
    } catch (problema) {
      setErro(problema instanceof Error ? problema.message : "Não deu para testar agora.");
    } finally {
      setRodando(false);
    }
  }
  return (
    <section className="mt-8 border-t border-borda pt-6">
      <p className="mb-3 text-sm text-muted">
        {pendente ? "Salve as alterações antes de testar." : "Cinco perguntas com os ajustes salvos. Consome IA como uma conversa."}
      </p>
      <Botao onClick={roda} disabled={pendente || rodando}>
        {rodando ? "Testando…" : "Ver como ele responde"}
      </Botao>
      {erro && <Aviso tom="erro" titulo="não deu para testar">{erro}</Aviso>}
      {casos.map((caso, i) => (
        <div key={caso.caso} className="mt-4 rounded-md border border-borda p-4">
          <p className="font-semibold">{caso.pergunta}</p>
          {anteriores[i] && <p className="mt-2 whitespace-pre-wrap text-sm text-muted">
            Antes: {anteriores[i].erro || anteriores[i].mensagens?.join("\n")}
          </p>}
          <p className="mt-2 whitespace-pre-wrap text-sm">{caso.erro || caso.mensagens?.join("\n")}</p>
          {caso.transferiu && <p className="mt-2 text-sm text-muted">Pediu transferência para uma pessoa.</p>}
        </div>
      ))}
    </section>
  );
}
