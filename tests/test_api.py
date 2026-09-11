"""Testes do contrato HTTP.

Nao chamam o modelo nem o banco: verificam validacao e autenticacao,
que sao deterministicas.
"""

from fastapi.testclient import TestClient

from app.main import app

cliente = TestClient(app)


def test_health_responde_ok():
    r = cliente.get("/health")
    assert r.status_code == 200
    assert r.json() == {"status": "ok"}


def test_chat_sem_cabecalho_de_chave():
    # 422 = requisicao malformada (falta header obrigatorio)
    r = cliente.post("/chat", json={"mensagem": "oi"})
    assert r.status_code == 422


def test_chat_com_chave_errada():
    r = cliente.post(
        "/chat",
        json={"mensagem": "oi"},
        headers={"x-api-key": "chave-errada"},
    )
    assert r.status_code == 401


def test_mensagem_vazia_e_recusada():
    r = cliente.post(
        "/chat",
        json={"mensagem": ""},
        headers={"x-api-key": "qualquer"},
    )
    assert r.status_code == 422


def test_mensagem_longa_demais_e_recusada():
    r = cliente.post(
        "/chat",
        json={"mensagem": "a" * 2001},
        headers={"x-api-key": "qualquer"},
    )
    assert r.status_code == 422
