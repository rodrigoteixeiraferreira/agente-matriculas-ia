"""Medicao de consumo e registro de log.

No nivel gratuito do Gemini o valor cobrado e zero. Ainda assim
medimos: o numero mostra quanto o sistema custaria se saisse do
nivel gratuito, que e a pergunta que importa antes de escalar.
"""

import logging

# Preco por MILHAO de tokens, em dolares, na faixa paga do flash-lite.
# Confira em ai.google.dev/pricing antes de citar numeros.
PRECO_ENTRADA_POR_MILHAO = 0.10
PRECO_SAIDA_POR_MILHAO = 0.40

log = logging.getLogger("agente")


def calcular_custo(tokens_entrada: int, tokens_saida: int) -> float:
    """Converte tokens em dolares equivalentes.

    Os tokens vem de `usage_metadata`, reportado pela propria API,
    nao de estimativa.
    """
    entrada = tokens_entrada / 1_000_000 * PRECO_ENTRADA_POR_MILHAO
    saida = tokens_saida / 1_000_000 * PRECO_SAIDA_POR_MILHAO
    return round(entrada + saida, 8)


def registrar(resultado: dict, custo: float) -> None:
    """Escreve uma linha de log estruturada por requisicao."""
    log.info(
        "chat concluido | chamadas_api=%d | ferramentas=%s | "
        "tokens_entrada=%d | tokens_saida=%d | custo_equivalente_usd=%.8f",
        resultado["chamadas_api"],
        resultado["ferramentas_usadas"],
        resultado["tokens_entrada"],
        resultado["tokens_saida"],
        custo,
    )
