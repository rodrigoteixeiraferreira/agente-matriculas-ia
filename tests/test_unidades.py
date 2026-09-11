"""Testes que nao dependem de banco nem da API do modelo."""

from app.observabilidade import calcular_custo
from app.tools import DECLARACOES, IMPLEMENTACOES


def test_custo_zero_quando_nao_ha_tokens():
    assert calcular_custo(0, 0) == 0.0


def test_saida_custa_mais_que_entrada():
    # Mesma quantidade de tokens, saida deve custar mais.
    assert calcular_custo(0, 1000) > calcular_custo(1000, 0)


def test_custo_cresce_com_o_volume():
    assert calcular_custo(2000, 0) > calcular_custo(1000, 0)


def test_toda_ferramenta_declarada_tem_implementacao():
    """Pega o bug de declarar uma ferramenta e esquecer de implementar."""
    declaradas = {d["name"] for d in DECLARACOES}
    assert declaradas == set(IMPLEMENTACOES.keys())


def test_toda_ferramenta_tem_descricao_util():
    """Descricao curta faz o modelo escolher errado."""
    for d in DECLARACOES:
        assert len(d["description"]) > 40, d["name"]
        assert d["parameters"]["type"] == "object"
        assert "properties" in d["parameters"]
