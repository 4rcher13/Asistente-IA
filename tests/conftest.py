"""Cierra VectorMemory tras cada test y al final de la sesión."""
import pytest
from src.core.vector_memory import shutdown_all_instances


@pytest.fixture(autouse=True)
def _shutdown_vector_memory_after_each_test():
    yield
    shutdown_all_instances(wait=False)


def pytest_sessionfinish(session, exitstatus):
    shutdown_all_instances(wait=False)
