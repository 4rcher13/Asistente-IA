"""
Fixtures reutilizables para tests
"""

import pytest
from unittest.mock import Mock, MagicMock


@pytest.fixture
def sample_user_data():
    """Datos de usuario para tests"""
    return {
        "email": "test@example.com",
        "password": "SecureTest123!",
        "full_name": "Test User"
    }


@pytest.fixture
def sample_query_data():
    """Datos de query para tests"""
    return {
        "query": "python programming",
        "limit": 10,
        "offset": 0
    }


@pytest.fixture
def mock_db_session():
    """Mock de sesión de BD"""
    mock = MagicMock()
    yield mock
    mock.close()


@pytest.fixture
def mock_cache():
    """Mock de caché"""
    mock = MagicMock()
    return mock
