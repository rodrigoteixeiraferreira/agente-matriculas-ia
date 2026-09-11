"""Ponto de entrada da aplicacao: rotas HTTP."""

import logging

from fastapi import FastAPI, Header, HTTPException, status

from app.agent import conversar
from app.config import settings
from app.models import ChatEntrada, ChatSaida
from app.observabilidade import calcular_custo, registrar

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s %(levelname)s %(message)s",
)

app = FastAPI(
    title="Agente de Matriculas",
    description=(
        "Atendimento a candidatos com IA: consulta de cursos, "
        "verificacao de vagas e pre-inscricao.\n\n"
        "Envie a `x-api-key` no cabecalho para usar o endpoint /chat."
    ),
    version="1.0.0",
)


def autenticar(chave: str) -> None:
    """Compara a chave recebida com a configurada."""
    if chave != settings.api_key:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Chave de API invalida.",
        )


@app.get("/health", tags=["infra"])
def health():
    """Verifica se o servico esta no ar."""
    return {"status": "ok"}


@app.post("/chat", response_model=ChatSaida, tags=["agente"])
def chat(entrada: ChatEntrada, x_api_key: str = Header(...)):
    """Envia uma mensagem ao agente e recebe a resposta.

    Devolva o campo `historico` na proxima chamada para manter o contexto.
    """
    autenticar(x_api_key)

    resultado = conversar(entrada.mensagem, entrada.historico)
    custo = calcular_custo(
        resultado["tokens_entrada"],
        resultado["tokens_saida"],
    )
    registrar(resultado, custo)

    return ChatSaida(**resultado, custo_equivalente_usd=custo)
