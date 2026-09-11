"""Acesso ao banco: pool de conexoes e funcoes de consulta."""

from contextlib import contextmanager

from psycopg.rows import dict_row
from psycopg_pool import ConnectionPool

from app.config import settings

# O pool comeca como None e so e criado na primeira consulta.
# Isso se chama inicializacao preguicosa (lazy).
#
# Por que importa: se o pool fosse criado aqui no topo, o simples ato
# de importar este arquivo ja tentaria conectar no banco. Nos testes
# automatizados, onde nao existe banco, isso gera erro e ruido.
_pool: ConnectionPool | None = None


def _configurar(conn) -> None:
    """Roda uma vez para cada conexao nova do pool.

    O pooler do Supabase (porta 6543) opera em modo transacao e NAO
    suporta prepared statements. O psycopg 3 passa a usar prepared
    statements a partir da 5a execucao da mesma consulta, o que
    quebraria em producao com um erro dificil de diagnosticar.

    prepare_threshold = None desliga esse comportamento.
    """
    conn.prepare_threshold = None


def obter_pool() -> ConnectionPool:
    """Devolve o pool, criando-o na primeira chamada."""
    global _pool
    if _pool is None:
        _pool = ConnectionPool(
            conninfo=settings.database_url,
            min_size=1,
            max_size=5,
            configure=_configurar,
            open=True,
        )
    return _pool


@contextmanager
def cursor():
    """Empresta uma conexao do pool e devolve ao final, sempre.

    O `with` garante a devolucao mesmo se a consulta lancar excecao.
    """
    with obter_pool().connection() as conn:
        with conn.cursor(row_factory=dict_row) as cur:
            yield cur


def buscar(sql: str, params: tuple = ()) -> list[dict]:
    """Executa uma consulta e devolve todas as linhas."""
    with cursor() as cur:
        cur.execute(sql, params)
        return cur.fetchall()


def buscar_um(sql: str, params: tuple = ()) -> dict | None:
    """Executa uma consulta e devolve a primeira linha (ou None)."""
    with cursor() as cur:
        cur.execute(sql, params)
        return cur.fetchone()
