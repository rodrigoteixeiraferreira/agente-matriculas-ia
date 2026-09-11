"""Configuracao do servico, lida de variaveis de ambiente."""

from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    # De onde ler as variaveis quando rodando local.
    # Em producao (Render) elas vem do ambiente, e o .env nem existe.
    model_config = SettingsConfigDict(env_file=".env", extra="ignore")

    # Sem valor padrao = obrigatoria. Se faltar, o servico nao sobe.
    gemini_api_key: str
    database_url: str
    api_key: str

    # Com valor padrao = opcional.
    # Confirme no Google AI Studio qual flash-lite a sua conta tem.
    model: str = "gemini-3.1-flash-lite"
    max_turnos: int = 6


# Instancia unica, importada pelos outros modulos.
# A validacao acontece nesta linha, quando o programa inicia.
settings = Settings()
