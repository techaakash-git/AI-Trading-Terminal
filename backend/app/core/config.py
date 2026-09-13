from pydantic import AliasChoices, Field
from pydantic_settings import BaseSettings, SettingsConfigDict

class Settings(BaseSettings):
    app_env: str = 'development'
    cors_origins: str = 'http://localhost:3000'
    market_provider: str = 'demo'
    market_api_key: str = Field('', validation_alias=AliasChoices('MARKET_API_KEY', 'TWELVEDATA_API_KEY'))
    database_url: str = 'postgresql+asyncpg://trading:trading_dev@localhost:5432/trading'
    redis_url: str = 'redis://localhost:6379/0'
    market_stale_after_seconds: int = 20
    ai_provider: str = 'disabled'
    news_provider: str = 'disabled'
    news_api_key: str = Field('', validation_alias=AliasChoices('NEWS_API_KEY', 'NEWSAPI_KEY'))
    ai_base_url: str = Field('', validation_alias=AliasChoices('AI_BASE_URL', 'ANTHROPIC_BASE_URL'))
    ai_auth_token: str = Field('', validation_alias=AliasChoices('AI_AUTH_TOKEN', 'ANTHROPIC_AUTH_TOKEN'))
    ai_model: str = Field('', validation_alias=AliasChoices('AI_MODEL', 'ANTHROPIC_MODEL'))
    model_config = SettingsConfigDict(env_file='.env', extra='ignore')

settings = Settings()
