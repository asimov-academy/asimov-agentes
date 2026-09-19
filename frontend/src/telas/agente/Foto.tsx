import { useRef, useState } from "react";
import { ErroDaApi, type Agente } from "../../api/cliente";
import { Avatar } from "../../design/Avatar";
import { Icone } from "../../design/Icone";

/** A cara do agente, na ficha: o retrato é o botão, e a seta no canto diz isso.
 *
 *  O botão de enviar ficava embaixo do retrato, como uma peça à parte; aqui ele é o próprio
 *  retrato, com o selo no canto (que aparece sempre, porque em tela de toque não existe passar o
 *  mouse) e o escurecido no hover. Remover só existe quando há o que remover.
 *
 *  Agente de WhatsApp chega com a foto do número pareado; esta daqui vale para os outros canais e
 *  para quem quer outra. A cor da inicial fica em Configurações.
 */
export function Foto({
  agente,
  aoEnviar,
  aoApagar,
}: {
  agente: Agente;
  aoEnviar: (arquivo: File) => Promise<void>;
  aoApagar: () => Promise<void>;
}) {
  const [ocupado, setOcupado] = useState(false);
  const [erro, setErro] = useState("");
  const seletor = useRef<HTMLInputElement>(null);

  async function faz(o_que: () => Promise<void>) {
    setOcupado(true);
    setErro("");
    try {
      await o_que();
    } catch (problema) {
      setErro(problema instanceof ErroDaApi ? problema.message : String(problema));
    } finally {
      setOcupado(false);
    }
  }

  return (
    <div className="flex flex-col items-center gap-1">
      <input
        ref={seletor}
        type="file"
        hidden
        accept="image/png,image/jpeg,image/webp"
        onChange={(e) => {
          const arquivo = e.target.files?.[0];
          e.target.value = "";
          if (arquivo) faz(() => aoEnviar(arquivo));
        }}
      />

      <div className="relative">
        <button
          onClick={() => seletor.current?.click()}
          disabled={ocupado}
          aria-label={agente.avatar ? "Trocar a foto" : "Enviar uma foto"}
          title={`${agente.avatar ? "Trocar a foto" : "Enviar uma foto"}: PNG, JPEG ou WebP, até 2 MB`}
          className="group/foto relative block rounded-md transition-opacity disabled:opacity-60"
        >
          <Avatar agente={agente} tamanho={96} />

          {/* O escurecido é só no hover; o selo do canto fica, para o toque também saber. */}
          <span className="absolute inset-0 rounded-md bg-void/50 opacity-0 transition-opacity group-hover/foto:opacity-100 group-focus-visible/foto:opacity-100" />
          <span className="absolute -bottom-1 -right-1 flex h-7 w-7 items-center justify-center rounded-full border border-borda bg-panel text-muted transition-colors group-hover/foto:border-ciano group-hover/foto:text-ciano">
            <Icone
              nome={ocupado ? "sys-girando" : "act-upload"}
              tamanho={14}
              className={ocupado ? "animate-spin" : ""}
            />
          </span>
        </button>

        {/* No canto de cima, e fora do botão do retrato: um botão não mora dentro do outro. O alvo
            se estende além do desenho, para o dedo não precisar de mira. */}
        {agente.avatar && (
          <button
            onClick={() => faz(aoApagar)}
            disabled={ocupado}
            aria-label="Remover a foto"
            title="Remover a foto"
            className="absolute -right-1 -top-1 flex h-7 w-7 items-center justify-center rounded-full border border-borda bg-panel text-muted transition-colors before:absolute before:-inset-2 before:content-[''] hover:border-perigo hover:text-perigo disabled:opacity-40"
          >
            <Icone nome="act-delete" tamanho={14} />
          </button>
        )}
      </div>

      {erro && (
        <p role="alert" className="max-w-[12rem] text-xs text-perigo">
          {erro}
        </p>
      )}
    </div>
  );
}
