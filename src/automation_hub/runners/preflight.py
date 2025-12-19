"""
Runner de preflight checks para validar configuración antes de ejecutar jobs.

Uso:
    python -m automation_hub.runners.preflight
"""
import logging
import os
import sys
import base64
import json
from automation_hub.config.logging import setup_logging

logger = logging.getLogger(__name__)


def decode_jwt_payload(token: str) -> dict:
    """
    Decodifica el payload de un JWT sin verificar firma.
    
    Args:
        token: JWT token
        
    Returns:
        Dict con el payload decodificado
    """
    try:
        # JWT tiene 3 partes separadas por puntos: header.payload.signature
        parts = token.split('.')
        if len(parts) != 3:
            raise ValueError("JWT debe tener 3 partes")
        
        # Decodificar payload (segunda parte)
        payload = parts[1]
        # Agregar padding si es necesario
        padding = 4 - (len(payload) % 4)
        if padding != 4:
            payload += '=' * padding
        
        decoded = base64.urlsafe_b64decode(payload)
        return json.loads(decoded)
    except Exception as e:
        logger.error(f"Error decodificando JWT: {e}")
        return {}


def validate_env_vars() -> bool:
    """
    Valida que todas las variables de entorno requeridas existan.
    
    Returns:
        True si todas las variables están presentes, False en caso contrario
    """
    required_vars = [
        "SUPABASE_URL",
        "SUPABASE_KEY",
        "GOOGLE_CLIENT_ID",
        "GOOGLE_CLIENT_SECRET",
        "GBP_REFRESH_TOKEN",
        "JOB_LIST"
    ]
    
    missing = []
    for var in required_vars:
        value = os.getenv(var)
        if not value or not value.strip():
            missing.append(var)
    
    if missing:
        logger.error(f"Variables faltantes: {', '.join(missing)}")
        return False
    
    logger.info("✓ Todas las variables requeridas están presentes")
    return True


def validate_supabase_key() -> bool:
    """
    Valida y decodifica el payload del JWT de Supabase.
    
    Returns:
        True si el JWT es válido, False en caso contrario
    """
    supabase_key = os.getenv("SUPABASE_KEY", "").strip()
    
    if not supabase_key:
        logger.error("SUPABASE_KEY vacía")
        return False
    
    payload = decode_jwt_payload(supabase_key)
    
    if not payload:
        logger.error("SUPABASE_KEY no es un JWT válido")
        return False
    
    # Loggear info del JWT (sin mostrar la key completa)
    logger.info(f"✓ SUPABASE_KEY JWT válido:")
    logger.info(f"  - role: {payload.get('role', 'N/A')}")
    logger.info(f"  - ref: {payload.get('ref', 'N/A')}")
    logger.info(f"  - exp: {payload.get('exp', 'N/A')}")
    logger.info(f"  - key_len: {len(supabase_key)}")
    
    return True


def validate_google_credentials() -> bool:
    """
    Valida formato básico de credenciales de Google.
    
    Returns:
        True si las credenciales tienen formato válido, False en caso contrario
    """
    client_id = os.getenv("GOOGLE_CLIENT_ID", "").strip()
    client_secret = os.getenv("GOOGLE_CLIENT_SECRET", "").strip()
    refresh_token = os.getenv("GBP_REFRESH_TOKEN", "").strip()
    
    valid = True
    
    if not client_id.endswith(".apps.googleusercontent.com"):
        logger.error("GOOGLE_CLIENT_ID debe terminar en .apps.googleusercontent.com")
        valid = False
    else:
        logger.info("✓ GOOGLE_CLIENT_ID formato válido")
    
    if len(client_secret) < 20:
        logger.error("GOOGLE_CLIENT_SECRET parece inválido (muy corto)")
        valid = False
    else:
        logger.info(f"✓ GOOGLE_CLIENT_SECRET longitud: {len(client_secret)}")
    
    if not refresh_token or len(refresh_token) < 30:
        logger.error("GBP_REFRESH_TOKEN parece inválido")
        valid = False
    else:
        logger.info(f"✓ GBP_REFRESH_TOKEN longitud: {len(refresh_token)}")
    
    return valid


def run_preflight() -> int:
    """
    Ejecuta todos los preflight checks.
    
    Returns:
        Exit code: 0 si todo OK, 2 si hay errores
    """
    setup_logging()
    logger.info("=== Ejecutando preflight checks ===")
    
    checks = [
        ("Variables de entorno", validate_env_vars),
        ("Supabase JWT", validate_supabase_key),
        ("Google credentials", validate_google_credentials)
    ]
    
    all_passed = True
    
    for check_name, check_func in checks:
        logger.info(f"\n--- {check_name} ---")
        if not check_func():
            all_passed = False
            logger.error(f"✗ {check_name} falló")
        else:
            logger.info(f"✓ {check_name} pasó")
    
    logger.info("\n=== Resumen ===")
    if all_passed:
        logger.info("✓ Todos los preflight checks pasaron")
        return 0
    else:
        logger.error("✗ Algunos preflight checks fallaron")
        return 2


def main() -> int:
    """Punto de entrada principal."""
    try:
        return run_preflight()
    except Exception as e:
        logger.exception(f"Error crítico en preflight: {e}")
        return 2


if __name__ == "__main__":
    sys.exit(main())
