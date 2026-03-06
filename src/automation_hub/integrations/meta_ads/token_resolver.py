"""Resolucion de tokens de Meta Ads desde BD y variables de entorno."""

from __future__ import annotations

import os
from datetime import datetime
from typing import Any, Dict, List, Optional, Sequence, Tuple


def _parse_dt(value: Optional[str]) -> Optional[datetime]:
    if not value:
        return None
    try:
        return datetime.fromisoformat(value.replace("Z", "+00:00"))
    except Exception:
        return None


def token_from_env() -> Tuple[Optional[str], Optional[str]]:
    """Fallback legacy por variables de entorno."""
    candidates = [
        "META_ACCESS_REDACTED_TOKEN",
        "META_ADS_ACCESS_TOKEN",
        "META_USER_ACCESS_TOKEN",
        "META_ACCESS_TOKEN",
    ]
    for var_name in candidates:
        value = os.getenv(var_name)
        if value and value.strip():
            return value.strip(), f"env:{var_name}"
    return None, None


def token_from_meta_tokens(supabase: Any, nombre_nora: Optional[str]) -> Tuple[Optional[str], Optional[str]]:
    """
    Obtiene token activo desde tabla public.meta_tokens.

    Prioridad por tipo: system > user > page.
    """
    if not nombre_nora:
        return None, None

    try:
        result = (
            supabase.table("meta_tokens")
            .select("id, token, subject_type, subject_id, status, expires_at, updated_at, issued_at")
            .eq("provider", "meta")
            .eq("status", "active")
            .eq("nombre_nora", nombre_nora)
            .not_.is_("token", "null")
            .execute()
        )
    except Exception:
        return None, None

    rows = result.data or []
    if not rows:
        return None, None

    now_utc = datetime.utcnow().replace(tzinfo=None)
    type_rank = {"system": 0, "user": 1, "page": 2}
    valid_rows: List[Dict[str, Any]] = []

    for row in rows:
        token = (row.get("token") or "").strip()
        if not token:
            continue

        expires_at = _parse_dt(row.get("expires_at"))
        if expires_at is not None and expires_at.replace(tzinfo=None) <= now_utc:
            continue

        valid_rows.append(row)

    if not valid_rows:
        return None, None

    def _sort_key(row: Dict[str, Any]) -> Tuple[int, datetime, datetime]:
        rank = type_rank.get((row.get("subject_type") or "").lower(), 99)
        expires = _parse_dt(row.get("expires_at"))
        updated = _parse_dt(row.get("updated_at")) or _parse_dt(row.get("issued_at")) or datetime.min
        expires_weight = expires.replace(tzinfo=None) if expires else datetime.max
        updated_weight = updated.replace(tzinfo=None)
        return (rank, expires_weight, updated_weight)

    chosen = sorted(valid_rows, key=_sort_key, reverse=False)[0]
    subject_type = chosen.get("subject_type") or "unknown"
    subject_id = chosen.get("subject_id") or "unknown"
    source = f"meta_tokens:{nombre_nora}:{subject_type}:{subject_id}"
    return chosen.get("token"), source


def resolve_meta_token(
    supabase: Any,
    nombre_nora: Optional[str],
    fallback_noras: Optional[Sequence[str]] = None,
    allow_env_fallback: bool = True,
) -> Tuple[Optional[str], Optional[str]]:
    """
    Resuelve token de Meta buscando por Nora y fallback de Noras.

    Orden:
    1) nombre_nora principal en meta_tokens
    2) fallback_noras en meta_tokens
    3) variables de entorno (si allow_env_fallback=True)
    """
    candidates: List[str] = []
    if nombre_nora:
        candidates.append(nombre_nora)
    for nora in fallback_noras or []:
        if nora and nora not in candidates:
            candidates.append(nora)

    for nora in candidates:
        token, source = token_from_meta_tokens(supabase, nora)
        if token:
            return token, source

    if allow_env_fallback:
        return token_from_env()

    return None, None
