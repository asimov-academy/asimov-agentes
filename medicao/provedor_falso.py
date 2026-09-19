"""Provedor de IA de mentira para a medição de recursos: fala o bastante da API da OpenAI
(Responses, transcrição e lista de modelos) para um turno inteiro rodar sem chave e sem gastar token.

Cada resposta demora `ATRASO_SEGUNDOS` (1 s por padrão), que é a ordem de grandeza de um modelo
rápido de verdade: sem a espera, o worker ficaria menos tempo com o turno aberto do que em produção.
Só biblioteca padrão, para rodar em `python:3.12-slim` sem instalar nada.
"""

import json
import os
import time
import uuid
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer

ATRASO_SEGUNDOS = float(os.environ.get("ATRASO_SEGUNDOS", "1"))
TEXTO = "Claro! Nosso horário é de segunda a sexta, das 9h às 18h. Posso ajudar em mais alguma coisa?"
USO = {
    "input_tokens": 900,
    "output_tokens": 40,
    "total_tokens": 940,
    "input_tokens_details": {"cached_tokens": 0},
    "output_tokens_details": {"reasoning_tokens": 0},
}


def _saida(pedido: dict) -> list[dict]:
    """O turno de conversa pede a resposta de dois jeitos (ver `tipo_de_saida` em `ia/agente.py`):
    pela ferramenta `final_result` ou por JSON Schema. As outras chamadas (visão, memória, resumo)
    querem texto puro."""
    estruturada = json.dumps({"mensagens": [TEXTO]}, ensure_ascii=False)
    for ferramenta in pedido.get("tools") or []:
        if ferramenta.get("name") == "final_result":
            return [
                {
                    "type": "function_call",
                    "id": f"fc_{uuid.uuid4().hex}",
                    "call_id": f"call_{uuid.uuid4().hex}",
                    "name": "final_result",
                    "arguments": estruturada,
                    "status": "completed",
                }
            ]
    formato = ((pedido.get("text") or {}).get("format") or {}).get("type")
    texto = estruturada if formato == "json_schema" else TEXTO
    return [
        {
            "type": "message",
            "id": f"msg_{uuid.uuid4().hex}",
            "status": "completed",
            "role": "assistant",
            "content": [{"type": "output_text", "text": texto, "annotations": []}],
        }
    ]


class Provedor(BaseHTTPRequestHandler):
    protocol_version = "HTTP/1.1"

    def log_message(self, *_: object) -> None:
        pass

    def _responde(self, corpo: dict, status: int = 200) -> None:
        dados = json.dumps(corpo).encode()
        self.send_response(status)
        self.send_header("Content-Type", "application/json")
        self.send_header("Content-Length", str(len(dados)))
        self.end_headers()
        self.wfile.write(dados)

    def do_GET(self) -> None:
        if self.path.startswith("/v1/models"):
            self._responde({"object": "list", "data": [{"id": "gpt-falso", "object": "model"}]})
        else:
            self._responde({"ok": True})

    def do_POST(self) -> None:
        bruto = self.rfile.read(int(self.headers.get("Content-Length") or 0))
        time.sleep(ATRASO_SEGUNDOS)
        if self.path.startswith("/v1/audio/transcriptions"):
            self._responde({"text": "Oi, queria saber o horário de vocês.", "usage": USO})
            return
        if not self.path.startswith("/v1/responses"):
            self._responde({"error": {"message": f"caminho sem resposta falsa: {self.path}"}}, 404)
            return
        pedido = json.loads(bruto or b"{}")
        self._responde(
            {
                "id": f"resp_{uuid.uuid4().hex}",
                "object": "response",
                "created_at": int(time.time()),
                "status": "completed",
                "model": pedido.get("model", "gpt-falso"),
                "output": _saida(pedido),
                "parallel_tool_calls": True,
                "tool_choice": "auto",
                "tools": [],
                "usage": USO,
            }
        )


if __name__ == "__main__":
    ThreadingHTTPServer(("0.0.0.0", 9000), Provedor).serve_forever()
