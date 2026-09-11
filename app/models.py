"""Contratos de entrada e saida da API.

O FastAPI usa estas classes para tres coisas ao mesmo tempo:
validar a requisicao, gerar a documentacao em /docs e converter
entre JSON e objeto Python.
"""

from pydantic import BaseModel, Field


class ChatEntrada(BaseModel):
    mensagem: str = Field(
        min_length=1,
        max_length=2000,
        description="Mensagem do candidato.",
        examples=["Quais cursos de tecnologia voces oferecem?"],
    )
    historico: list = Field(
        default_factory=list,
        description="Historico devolvido na resposta anterior. "
                    "Deixe vazio para iniciar uma conversa.",
        # examples=[[]] faz o /docs mostrar uma lista vazia em vez do
        # texto de exemplo "string", que nao e um historico valido.
        examples=[[]],
    )


class ChatSaida(BaseModel):
    resposta: str
    historico: list
    ferramentas_usadas: list[str]
    chamadas_api: int
    custo_equivalente_usd: float
    tokens_entrada: int
    tokens_saida: int
