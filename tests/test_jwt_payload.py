"""
Tests para decodificación de JWT payload.
"""
import pytest
from automation_hub.runners.preflight import decode_jwt_payload


def test_decode_jwt_valid():
    """Debe decodificar un JWT válido."""
    # JWT dummy con payload: {"test": "value", "num": 123}
    token = "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.eyJ0ZXN0IjoidmFsdWUiLCJudW0iOjEyM30.signature"
    
    payload = decode_jwt_payload(token)
    
    assert payload is not None
    assert payload["test"] == "value"
    assert payload["num"] == 123


def test_decode_jwt_supabase_format():
    """Debe decodificar un JWT de Supabase."""
    # JWT dummy con formato similar a Supabase
    # Payload: {"iss": "supabase", "role": "service_role", "ref": "test"}
    token = "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.eyJpc3MiOiJzdXBhYmFzZSIsInJvbGUiOiJzZXJ2aWNlX3JvbGUiLCJyZWYiOiJ0ZXN0In0.signature"
    
    payload = decode_jwt_payload(token)
    
    assert payload["iss"] == "supabase"
    assert payload["role"] == "service_role"
    assert payload["ref"] == "test"


def test_decode_jwt_invalid_format():
    """Debe retornar dict vacío para JWT inválido."""
    assert decode_jwt_payload("not.a.jwt") == {}
    assert decode_jwt_payload("invalid") == {}
    assert decode_jwt_payload("") == {}


def test_decode_jwt_wrong_parts():
    """Debe retornar dict vacío si JWT no tiene 3 partes."""
    assert decode_jwt_payload("header.payload") == {}
    assert decode_jwt_payload("only_one_part") == {}
