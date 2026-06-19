"""
Configuración global para pytest
Define fixtures, hooks y utilidades compartidas
"""

import sys
from pathlib import Path
import pytest
from unittest.mock import Mock, patch

# Agregar src al path
sys.path.insert(0, str(Path(__file__).parent.parent))


# ==== FIXTURES GLOBALES ====

@pytest.fixture(scope="session")
def test_config():
    """Configuración para tests"""
    return {
        "ENVIRONMENT": "testing",
        "DEBUG": True,
        "DATABASE_URL": "sqlite:///:memory:",
        "REDIS_URL": "redis://localhost:6379/1"
    }


@pytest.fixture
def mock_logger():
    """Mock de logger"""
    return Mock()


@pytest.fixture
def mock_db():
    """Mock de base de datos"""
    return Mock()


@pytest.fixture
def mock_redis():
    """Mock de Redis"""
    return Mock()


# ==== CONFIGURACIÓN DE MARKERS ====

def pytest_configure(config):
    """Registra marcadores personalizados"""
    config.addinivalue_line("markers", "unit: unit tests")
    config.addinivalue_line("markers", "integration: integration tests")
    config.addinivalue_line("markers", "security: security tests")


# ==== HOOKS ====

def pytest_runtest_setup(item):
    """Setup antes de cada test"""
    pass


def pytest_runtest_teardown(item):
    """Cleanup después de cada test"""
    pass
