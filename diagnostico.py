#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Diagnostico: testa cada camada do sistema separadamente.

Rode de dentro da pasta do projeto, com o ambiente ativado:

    python diagnostico.py

Ele diz exatamente qual peca esta quebrada, em vez de um 500 generico.
"""

import sys
import traceback


def secao(titulo: str) -> None:
    print()
    print("=" * 62)
    print(titulo)
    print("=" * 62)


def ok(msg: str) -> None:
    print("  [OK]  " + msg)


def falha(msg: str) -> None:
    print("  [XX]  " + msg)


# ---------------------------------------------------------------
# 1. CONFIGURACAO
# ---------------------------------------------------------------
secao("1. Variaveis de ambiente")

try:
    from app.config import settings
except Exception as e:
    falha(f"Nao consegui carregar a configuracao: {e}")
    print()
    print("  Causa provavel: o arquivo .env nao existe, esta incompleto,")
    print("  ou voce nao esta na pasta do projeto.")
    sys.exit(1)

chave_gemini = settings.gemini_api_key or ""
url_banco = settings.database_url or ""

if len(chave_gemini) < 20:
    falha(f"GEMINI_API_KEY parece invalida (tem {len(chave_gemini)} caracteres)")
else:
    ok(f"GEMINI_API_KEY carregada ({chave_gemini[:6]}...{chave_gemini[-4:]})")

if not url_banco.startswith("postgres"):
    falha("DATABASE_URL nao parece uma string de conexao PostgreSQL")
    print(f"        valor atual: {url_banco[:40]}...")
elif "[YOUR-PASSWORD]" in url_banco or "cole-a-string" in url_banco:
    falha("DATABASE_URL ainda tem o texto de exemplo — falta trocar a senha")
else:
    # esconde a senha ao mostrar
    visivel = url_banco
    if "@" in visivel:
        antes, depois = visivel.split("@", 1)
        if ":" in antes:
            visivel = antes.rsplit(":", 1)[0] + ":****@" + depois
    ok(f"DATABASE_URL carregada ({visivel[:55]}...)")

ok(f"MODEL configurado: {settings.model}")
ok(f"API_KEY do servico: {'definida' if settings.api_key else 'VAZIA'}")


# ---------------------------------------------------------------
# 2. BANCO DE DADOS
# ---------------------------------------------------------------
secao("2. Conexao com o banco")

banco_ok = False
conexao = None
try:
    import psycopg
    from psycopg.rows import dict_row

    # Conexao direta, com timeout curto: o pool tentaria por 30s
    # antes de desistir, o que atrasaria demais o diagnostico.
    print("  conectando (ate 10s)...")
    conexao = psycopg.connect(url_banco, connect_timeout=10,
                              row_factory=dict_row)
    conexao.prepare_threshold = None
    with conexao.cursor() as cur:
        cur.execute("select 1 as teste")
        ok(f"Conectou. Resposta: {cur.fetchone()}")
    banco_ok = True
except Exception as e:
    falha(f"{type(e).__name__}: {str(e)[:200]}")
    print()
    print("  Causas provaveis:")
    print("   - senha errada na DATABASE_URL")
    print("   - usou a string direta em vez da do pooler (porta 6543)")
    print("   - projeto do Supabase ainda iniciando")


def consulta(sql: str):
    with conexao.cursor() as cur:
        cur.execute(sql)
        return cur.fetchall()


if banco_ok:
    try:
        cursos = consulta("select count(*) as n from cursos")
        n = cursos[0]["n"]
        if n == 0:
            falha("A tabela cursos existe mas esta VAZIA — falta rodar o seed.sql")
        else:
            ok(f"Tabela cursos tem {n} registros")
    except Exception as e:
        falha(f"Tabela cursos: {type(e).__name__}: {e}")
        print("        Falta rodar o sql/schema.sql no SQL Editor do Supabase.")

    try:
        t = consulta("select vagas_disponiveis(2) as v")
        ok(f"Funcao vagas_disponiveis(2) devolveu: {t[0]['v']}")
    except Exception as e:
        falha(f"Funcao vagas_disponiveis: {type(e).__name__}: {e}")


# ---------------------------------------------------------------
# 3. FERRAMENTAS
# ---------------------------------------------------------------
secao("3. Ferramentas do agente")

if not banco_ok:
    print("  (pulado: depende do banco)")
else:
    try:
        from app.tools import buscar_cursos, verificar_turmas

        r = buscar_cursos("tecnologia")
        ok(f"buscar_cursos('tecnologia') devolveu {len(r)} resultado(s)")
        if r:
            print(f"        primeiro: {r[0]['nome']}")

        t = verificar_turmas(2)
        ok(f"verificar_turmas(2) devolveu {len(t)} turma(s)")
        if t:
            print(f"        vagas: {t[0]['vagas_disponiveis']}, "
                  f"inscricoes abertas: {t[0]['inscricoes_abertas']}")
    except Exception as e:
        falha(f"{type(e).__name__}: {e}")
        traceback.print_exc()


# ---------------------------------------------------------------
# 4. API DO GEMINI
# ---------------------------------------------------------------
secao("4. API do Gemini")

gemini_ok = False
try:
    from google import genai

    cliente = genai.Client(api_key=settings.gemini_api_key)
    resposta = cliente.models.generate_content(
        model=settings.model,
        contents="Responda apenas: funcionando",
    )
    ok(f"Modelo {settings.model} respondeu: {resposta.text!r}")
    uso = resposta.usage_metadata
    ok(f"Tokens — entrada: {uso.prompt_token_count}, "
       f"saida: {uso.candidates_token_count}")
    gemini_ok = True
except Exception as e:
    falha(f"{type(e).__name__}: {e}")
    texto = str(e).lower()
    print()
    if "not found" in texto or "404" in texto:
        print("  O NOME DO MODELO esta errado para a sua conta.")
        print("  Abra o Google AI Studio, veja quais modelos aparecem,")
        print("  e ajuste a variavel MODEL no .env.")
        print("  Alternativas comuns: gemini-2.5-flash-lite,")
        print("                       gemini-3.1-flash-lite")
    elif "api key" in texto or "401" in texto or "403" in texto:
        print("  A CHAVE esta invalida ou sem permissao.")
        print("  Gere outra em aistudio.google.com/apikey")
    elif "429" in texto or "quota" in texto or "resource" in texto:
        print("  Estourou o limite de requisicoes. Espere um minuto.")


# ---------------------------------------------------------------
# 5. LACO COMPLETO
# ---------------------------------------------------------------
secao("5. Laco do agente (ponta a ponta)")

if not (banco_ok and gemini_ok):
    print("  (pulado: resolva os itens acima primeiro)")
else:
    try:
        from app.agent import conversar

        r = conversar("quais cursos de tecnologia voces tem?")
        ok(f"Resposta: {r['resposta'][:120]}")
        ok(f"Ferramentas usadas: {r['ferramentas_usadas']}")
        ok(f"Chamadas a API: {r['chamadas_api']}")
        ok(f"Tokens: {r['tokens_entrada']} entrada / {r['tokens_saida']} saida")
        if not r["ferramentas_usadas"]:
            print()
            print("  ATENCAO: o modelo respondeu SEM consultar o banco.")
            print("  Pergunte de forma mais especifica, ou revise as")
            print("  descricoes das ferramentas em app/tools.py.")
    except Exception as e:
        falha(f"{type(e).__name__}: {e}")
        traceback.print_exc()


secao("Fim")
print("Se tudo acima estiver [OK], o /chat no /docs vai funcionar.")
print()
