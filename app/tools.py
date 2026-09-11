"""Ferramentas do agente.

Cada ferramenta tem duas partes:
  1. a IMPLEMENTACAO  - a funcao Python que realmente roda
  2. a DECLARACAO     - o JSON Schema que o modelo enxerga

O modelo nunca executa nada. Ele le a declaracao, decide qual
ferramenta quer e com quais argumentos, e devolve esse pedido.
Quem executa e o codigo abaixo.
"""

import json

from app.db import buscar, buscar_um

# ===============================================================
# IMPLEMENTACOES
# ===============================================================


def buscar_cursos(termo: str = "") -> list[dict]:
    """Busca cursos ativos por nome, area ou descricao."""
    if termo:
        sql = """
            select c.id, c.nome, c.area, c.modalidade,
                   c.duracao_meses, c.mensalidade, c.descricao
            from cursos c
            where c.ativo
              and (c.nome ilike %s or c.area ilike %s or c.descricao ilike %s)
            order by c.nome
            limit 5
        """
        alvo = f"%{termo}%"
        return buscar(sql, (alvo, alvo, alvo))

    return buscar(
        """
        select id, nome, area, modalidade, duracao_meses, mensalidade, descricao
        from cursos
        where ativo
        order by nome
        limit 5
        """
    )


def verificar_turmas(curso_id: int) -> list[dict]:
    """Lista turmas de um curso, com vagas calculadas em tempo real."""
    return buscar(
        """
        select t.id as turma_id,
               t.codigo,
               t.inicio,
               t.inscricoes_ate,
               vagas_disponiveis(t.id) as vagas_disponiveis,
               (t.inscricoes_ate >= current_date) as inscricoes_abertas
        from turmas t
        where t.curso_id = %s
        order by t.inicio
        """,
        (curso_id,),
    )


def criar_pre_inscricao(turma_id: int, nome: str, email: str,
                        telefone: str) -> dict:
    """Cria a pre-inscricao chamando a funcao do banco.

    Toda a regra (prazo, vaga, duplicidade, concorrencia) esta na
    funcao SQL. Aqui e so a ponte.
    """
    linha = buscar_um(
        "select criar_pre_inscricao(%s, %s, %s, %s) as r",
        (turma_id, nome, email, telefone),
    )
    return linha["r"]


# ===============================================================
# DECLARACOES (o que o modelo enxerga)
# ===============================================================

# As declaracoes usam "parameters" (formato do Gemini), nao
# "input_schema" (formato da Anthropic). O conteudo interno e o
# mesmo JSON Schema nos dois casos.
DECLARACOES = [
    {
        "name": "buscar_cursos",
        "description": (
            "Busca cursos ofertados pela instituicao. Use quando o candidato "
            "perguntar sobre cursos, areas de estudo, valores ou modalidades. "
            "Deixe o termo vazio para listar a oferta geral."
        ),
        "parameters": {
            "type": "object",
            "properties": {
                "termo": {
                    "type": "string",
                    "description": "Palavra-chave, area ou nome do curso.",
                }
            },
            "required": [],
        },
    },
    {
        "name": "verificar_turmas",
        "description": (
            "Lista as turmas de um curso com data de inicio, prazo de "
            "inscricao e vagas disponiveis. Use SEMPRE antes de oferecer "
            "inscricao, para confirmar que ha vaga e que o prazo esta aberto."
        ),
        "parameters": {
            "type": "object",
            "properties": {
                "curso_id": {
                    "type": "integer",
                    "description": "ID do curso, obtido em buscar_cursos.",
                }
            },
            "required": ["curso_id"],
        },
    },
    {
        "name": "criar_pre_inscricao",
        "description": (
            "Registra a pre-inscricao do candidato em uma turma. "
            "So chame depois de ter nome completo, email e telefone "
            "confirmados pelo candidato."
        ),
        "parameters": {
            "type": "object",
            "properties": {
                "turma_id": {"type": "integer",
                             "description": "ID da turma escolhida."},
                "nome":     {"type": "string",
                             "description": "Nome completo do candidato."},
                "email":    {"type": "string",
                             "description": "Email de contato."},
                "telefone": {"type": "string",
                             "description": "Telefone com DDD."},
            },
            "required": ["turma_id", "nome", "email", "telefone"],
        },
    },
]

# Liga o nome declarado a funcao real.
IMPLEMENTACOES = {
    "buscar_cursos": buscar_cursos,
    "verificar_turmas": verificar_turmas,
    "criar_pre_inscricao": criar_pre_inscricao,
}


def executar(nome: str, argumentos: dict) -> dict:
    """Executa uma ferramenta e devolve o resultado como dicionario.

    O Gemini exige que a resposta de funcao seja um objeto, por isso
    devolvemos dict e nao texto JSON.

    Nunca lanca excecao: um erro vira resultado, para o modelo poder
    se recuperar em vez de derrubar a requisicao inteira.
    """
    fn = IMPLEMENTACOES.get(nome)
    if fn is None:
        return {"erro": f"ferramenta desconhecida: {nome}"}

    try:
        resultado = fn(**argumentos)
        # Passa por json para converter date e Decimal, que o
        # protocolo nao conhece. default=str resolve os dois.
        return {"resultado": json.loads(json.dumps(resultado, default=str))}
    except Exception as e:
        return {"erro": type(e).__name__, "detalhe": str(e)}
