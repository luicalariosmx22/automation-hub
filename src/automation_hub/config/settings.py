"""Configuración centralizada de Automation Hub.

Este módulo carga las variables principales que consumen los jobs y expone
helpers específicos (por ejemplo, tokens de Telegram o WhatsApp). La meta es
eliminar lecturas dispersas de ``os.getenv`` en el código y usar una sola
fuente de verdad.
"""

from __future__ import annotations

import os
from dataclasses import dataclass
from functools import lru_cache
from typing import Any, Dict, Optional


def _getenv(name: str, default: Optional[str] = None) -> Optional[str]:
    value = os.getenv(name, default)
    return value.strip() if isinstance(value, str) else value


@dataclass(frozen=True)
class TelegramConfig:
    bot_token: Optional[str]
    default_chat_id: Optional[str]
    citas_bot_token: Optional[str]


@dataclass(frozen=True)
class WhatsAppConfig:
    server_url: Optional[str]
    alert_phone: Optional[str]


@dataclass(frozen=True)
class MetaConfig:
    access_token: Optional[str]
    ads_access_token: Optional[str]
    user_access_token: Optional[str]
    api_version: str


@dataclass(frozen=True)
class GoogleConfig:
    client_id: Optional[str]
    client_secret: Optional[str]
    refresh_token: Optional[str]
    oauth_client_id: Optional[str]
    oauth_client_secret: Optional[str]


@dataclass(frozen=True)
class Settings:
    log_level: str
    environment: str
    timezone: str
    supabase_url: Optional[str]
    supabase_key: Optional[str]
    telegram: TelegramConfig
    whatsapp: WhatsAppConfig
    meta: MetaConfig
    google: GoogleConfig


@lru_cache()
def load_settings() -> Settings:
    return Settings(
        log_level=_getenv("LOG_LEVEL", "INFO") or "INFO",
        environment=_getenv("ENVIRONMENT", "development") or "development",
        timezone=_getenv("TZ", "UTC") or "UTC",
        supabase_url=_getenv("SUPABASE_URL"),
        supabase_key=_getenv("SUPABASE_KEY"),
        telegram=TelegramConfig(
            bot_token=_getenv("TELEGRAM_BOT_TOKEN"),
            default_chat_id=_getenv("TELEGRAM_CHAT_ID"),
            citas_bot_token=_getenv("TELEGRAM_BOT_TOKEN_CITAS"),
        ),
        whatsapp=WhatsAppConfig(
            server_url=_getenv("WHATSAPP_SERVER_URL"),
            alert_phone=_getenv("WHATSAPP_ALERT_PHONE"),
        ),
        meta=MetaConfig(
            access_token=_getenv("META_ACCESS_REDACTED_TOKEN"),
            ads_access_token=_getenv("META_ADS_ACCESS_TOKEN"),
            user_access_token=_getenv("META_USER_ACCESS_TOKEN"),
            api_version=_getenv("META_API_VERSION", "v23.0") or "v23.0",
        ),
        google=GoogleConfig(
            client_id=_getenv("GOOGLE_CLIENT_ID"),
            client_secret=_getenv("GOOGLE_CLIENT_SECRET"),
            refresh_token=_getenv("GBP_REFRESH_TOKEN"),
            oauth_client_id=_getenv("GOOGLE_OAUTH_CLIENT_ID"),
            oauth_client_secret=_getenv("GOOGLE_OAUTH_CLIENT_SECRET"),
        ),
    )


def as_dict() -> Dict[str, Any]:
    settings = load_settings()
    return {
        "log_level": settings.log_level,
        "environment": settings.environment,
        "timezone": settings.timezone,
        "supabase_url": settings.supabase_url,
        "supabase_key": settings.supabase_key,
    }
