"""
Tests para función de limpieza de variables de entorno.
"""
import pytest
from automation_hub.db.supabase_client import _clean_env


def test_clean_env_none():
    """Debe retornar None si el input es None."""
    assert _clean_env(None) is None


def test_clean_env_empty():
    """Debe retornar string vacío si el input está vacío después de strip."""
    assert _clean_env("") == ""
    assert _clean_env("   ") == ""


def test_clean_env_spaces():
    """Debe remover espacios al inicio y final."""
    assert _clean_env("  test  ") == "test"
    assert _clean_env("\ttest\n") == "test"


def test_clean_env_double_quotes():
    """Debe remover comillas dobles envolventes."""
    assert _clean_env('"test"') == "test"
    assert _clean_env('"  test  "') == "test"


def test_clean_env_single_quotes():
    """Debe remover comillas simples envolventes."""
    assert _clean_env("'test'") == "test"
    assert _clean_env("'  test  '") == "test"


def test_clean_env_no_quotes():
    """No debe modificar strings sin comillas envolventes."""
    assert _clean_env("test") == "test"
    assert _clean_env('test"with"quotes') == 'test"with"quotes'


def test_clean_env_mixed_quotes():
    """No debe remover comillas si no coinciden."""
    assert _clean_env('"test\'') == '"test\''
    assert _clean_env('\'test"') == '\'test"'


def test_clean_env_single_quote():
    """No debe fallar con un solo carácter."""
    assert _clean_env('"') == '"'
    assert _clean_env("'") == "'"
    assert _clean_env("a") == "a"
