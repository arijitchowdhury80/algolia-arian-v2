"""PRISM Platform configuration via Pydantic Settings.

LLM Provider Selection:
  Set ENRICHER_PROVIDER to choose which LLM powers the enrichment step.
  Supported values: "anthropic", "gemini", "openai", "openrouter"
  The app auto-detects based on which API key is set if ENRICHER_PROVIDER is not specified.
  Priority: anthropic > openai > gemini > openrouter

  Set ENRICHER_MODEL to override the default model for the selected provider.
  Defaults:
    anthropic  → claude-haiku-4-5-20251001  (cost-effective for structuring)
    gemini     → gemini-2.0-flash
    openai     → gpt-4o-mini
    openrouter → google/gemini-2.0-flash-001
"""

from __future__ import annotations

from typing import Literal

import structlog
from pydantic_settings import BaseSettings, SettingsConfigDict

logger = structlog.get_logger(__name__)


class Settings(BaseSettings):
    """Application settings loaded from environment variables."""

    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        case_sensitive=False,
    )

    # Application
    app_env: Literal["development", "staging", "production"] = "development"
    log_level: Literal["DEBUG", "INFO", "WARNING", "ERROR"] = "INFO"

    # PostgreSQL
    database_url: str = "postgresql+asyncpg://prism:prism_dev_password@localhost:5432/prism"

    # Redis
    redis_url: str = "redis://localhost:6379/0"

    # Temporal
    temporal_host: str = "localhost:7233"
    temporal_namespace: str = "default"
    temporal_task_queue: str = "prism-audit-queue"

    # --- LLM Providers ---

    # Anthropic (Claude)
    anthropic_api_key: str = ""

    # OpenAI
    openai_api_key: str = ""

    # Google Gemini
    gemini_api_key: str = ""

    # OpenRouter (access any model via unified API)
    openrouter_api_key: str = ""

    # --- Enricher LLM Configuration ---

    # Which provider to use for module enrichment.
    # Auto-detected from API keys if not set.
    enricher_provider: str = ""

    # Override the default model for the selected provider.
    # Leave empty to use the cost-effective default for each provider.
    enricher_model: str = ""

    # --- Data Source APIs ---

    # BuiltWith
    builtwith_api_key: str = ""

    # Perplexity (web intelligence)
    perplexity_api_key: str = ""

    # SimilarWeb (traffic analytics)
    similarweb_api_key: str = ""

    # Apify (LinkedIn scraping)
    apify_api_key: str = ""

    # Crossbeam (partner overlap)
    crossbeam_api_key: str = ""

    # Tavily (backup research API)
    tavily_api_key: str = ""

    # SerpApi (Google SERP results)
    serpapi_api_key: str = ""

    # Perplexity model (sonar = $0.25/M input, sonar-pro = $3/M input)
    perplexity_model: str = "sonar"

    # Staleness thresholds (days) — how long before each module's data is considered stale
    staleness_thresholds: dict[str, int] = {
        "intel-news": 14,
        "intel-hiring": 30,
        "intel-social": 30,
        "intel-traffic": 30,
        "intel-competitors": 60,
        "audit-browser": 60,
        "intel-techstack": 90,
        "intel-financial-public": 90,
        "intel-financial-private": 90,
        "intel-investor": 90,
        "intel-queries": 90,
        "intel-company": 180,
        "intel-partner": 180,
        "intel-industry": 180,
    }

    # Voice (placeholder)
    voice_enabled: bool = False
    voice_wake_word: str = "Hey aRRIe, wake up"

    def get_enricher_provider(self) -> str:
        """Determine which LLM provider to use for enrichment.

        Priority: explicit setting > anthropic > openai > gemini > openrouter

        Returns:
            Provider name: "anthropic", "openai", "gemini", or "openrouter"

        Raises:
            ValueError: If no LLM provider is configured.
        """
        if self.enricher_provider:
            return self.enricher_provider

        if self.anthropic_api_key:
            return "anthropic"
        if self.openai_api_key:
            return "openai"
        if self.gemini_api_key:
            return "gemini"
        if self.openrouter_api_key:
            return "openrouter"

        raise ValueError(
            "No LLM provider configured. Set at least one of: "
            "ANTHROPIC_API_KEY, OPENAI_API_KEY, GEMINI_API_KEY, or OPENROUTER_API_KEY"
        )

    def get_enricher_model(self) -> str:
        """Get the model ID for the current enricher provider.

        Returns the explicit ENRICHER_MODEL if set, otherwise the
        cost-effective default for the detected provider.
        """
        if self.enricher_model:
            return self.enricher_model

        provider = self.get_enricher_provider()
        defaults = {
            "anthropic": "claude-haiku-4-5-20251001",
            "openai": "gpt-4o-mini",
            "gemini": "gemini-2.0-flash",
            "openrouter": "google/gemini-2.0-flash-001",
        }
        return defaults.get(provider, "claude-haiku-4-5-20251001")


settings = Settings()

# Log the resolved provider at startup
try:
    _provider = settings.get_enricher_provider()
    _model = settings.get_enricher_model()
    logger.info(
        "LLM enricher configured",
        provider=_provider,
        model=_model,
    )
except ValueError:
    logger.warning("No LLM provider configured — enrichment will fail")
