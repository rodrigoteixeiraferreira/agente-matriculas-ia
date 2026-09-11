"""O laco do agente, sobre a API do Gemini.

Escrito a mao, sem framework de orquestracao e com a chamada
automatica de funcoes do SDK desligada, para manter controle
explicito sobre execucao, limite de turnos e tratamento de erro.
"""

import logging

from google import genai
from google.genai import types

from app.config import settings
from app.tools import DECLARACOES, executar

log = logging.getLogger("agente")

cliente = genai.Client(api_key=settings.gemini_api_key)

# Uma Tool agrupa as declaracoes de funcao que o modelo pode pedir.
FERRAMENTAS = types.Tool(function_declarations=DECLARACOES)

INSTRUCOES = """Voce atende candidatos interessados nos cursos da instituicao.

Como agir:
- Seja direto e cordial. Respostas curtas, sem enrolacao.
- Descubra a area de interesse antes de listar cursos.
- Antes de oferecer inscricao, verifique turmas e vagas com a ferramenta.
- Nunca afirme que ha vaga sem ter consultado. Nunca invente valor,
  data ou prazo: tudo vem das ferramentas.
- Para inscrever, colete nome completo, email e telefone, confirme os
  dados com o candidato e so entao registre.
- Se nao houver vaga ou o prazo estiver encerrado, diga com clareza e
  ofereca alternativa.
- Voce nao negocia preco, desconto ou excecao de prazo. Nesses casos,
  encaminhe para um atendente humano.
"""

CONFIG = types.GenerateContentConfig(
    system_instruction=INSTRUCOES,
    tools=[FERRAMENTAS],
    # O SDK do Gemini sabe executar funcoes sozinho. Desligamos de
    # proposito: queremos o laco explicito, com limite de turnos e
    # tratamento de erro sob nosso controle.
    automatic_function_calling=types.AutomaticFunctionCallingConfig(
        disable=True
    ),
)


def _tokens(resposta) -> tuple[int, int]:
    """Extrai o consumo reportado pela API, com tolerancia a ausencia."""
    uso = getattr(resposta, "usage_metadata", None)
    if uso is None:
        return 0, 0
    entrada = getattr(uso, "prompt_token_count", 0) or 0
    saida = getattr(uso, "candidates_token_count", 0) or 0
    return entrada, saida


def _normalizar(historico: list | None) -> list:
    """Converte o historico recebido em objetos Content.

    Quem consome a API devolve o historico como JSON, entao ele chega
    aqui como lista de dicionarios. O SDK precisa de objetos Content.
    """
    saida = []
    for item in historico or []:
        if isinstance(item, types.Content):
            saida.append(item)
        elif isinstance(item, dict):
            saida.append(types.Content.model_validate(item))
        else:
            # Ignora entradas que nao sao conversa. O caso comum e o
            # texto de exemplo do Swagger ("string"), que chegaria aqui
            # e derrubaria a requisicao inteira com erro 500.
            log.warning("historico: item ignorado (%s)", type(item).__name__)
    return saida


def conversar(mensagem: str, historico: list | None = None) -> dict:
    """Executa o laco ate uma resposta final.

    `historico` e uma lista de types.Content. Devolve a resposta, o
    historico atualizado, as ferramentas usadas e o consumo.
    """
    # list() faz uma copia: nao alteramos a lista que veio de fora.
    conteudos = _normalizar(historico)
    conteudos.append(
        types.Content(role="user", parts=[types.Part(text=mensagem)])
    )

    tokens_entrada = 0
    tokens_saida = 0
    chamadas_api = 0
    ferramentas_usadas: list[str] = []

    for _ in range(settings.max_turnos):
        # ---- 1. Manda a conversa, as instrucoes e as ferramentas ----
        resposta = cliente.models.generate_content(
            model=settings.model,
            contents=conteudos,
            config=CONFIG,
        )
        chamadas_api += 1

        entrada, saida = _tokens(resposta)
        tokens_entrada += entrada
        tokens_saida += saida

        # ---- 2. Guarda a resposta do modelo no historico ------------
        candidato = resposta.candidates[0]
        conteudos.append(candidato.content)

        # ---- 3. Nao pediu funcao? entao e a resposta final ----------
        pedidos = resposta.function_calls or []
        if not pedidos:
            texto = "".join(
                parte.text
                for parte in (candidato.content.parts or [])
                if getattr(parte, "text", None)
            )
            return {
                "resposta": texto.strip(),
                "historico": conteudos,
                "ferramentas_usadas": ferramentas_usadas,
                "chamadas_api": chamadas_api,
                "tokens_entrada": tokens_entrada,
                "tokens_saida": tokens_saida,
            }

        # ---- 4. Pediu funcao: executa e devolve o resultado ---------
        partes_resposta = []
        for pedido in pedidos:
            ferramentas_usadas.append(pedido.name)
            saida_ferramenta = executar(pedido.name, dict(pedido.args or {}))
            partes_resposta.append(
                types.Part.from_function_response(
                    name=pedido.name,
                    response=saida_ferramenta,
                )
            )

        conteudos.append(
            types.Content(role="user", parts=partes_resposta)
        )
        # ---- 5. Volta ao passo 1 com o dado real em maos ------------

    # Estourou o limite de turnos: degrada com elegancia.
    return {
        "resposta": "Nao consegui concluir agora. Vou encaminhar para um "
                    "atendente humano.",
        "historico": conteudos,
        "ferramentas_usadas": ferramentas_usadas,
        "chamadas_api": chamadas_api,
        "tokens_entrada": tokens_entrada,
        "tokens_saida": tokens_saida,
    }
