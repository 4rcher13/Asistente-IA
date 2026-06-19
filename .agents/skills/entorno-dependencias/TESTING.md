# 🧪 Guía de Testing - Asistente IA

## Estructura de Tests

\\\
tests/
├── __init__.py
├── conftest.py (configuración global)
├── unit/
│   ├── test_config.py
│   ├── test_security.py
│   ├── schemas/
│   │   └── test_validation.py
│   └── domain/
├── integration/
│   ├── test_database.py
│   └── test_api.py
├── e2e/
├── fixtures/
│   └── __init__.py
└── factories/
    └── __init__.py
\\\

## Ejecutar Tests

### Todos los tests
\\\ash
pytest tests/ -v
\\\

### Solo tests unitarios
\\\ash
pytest tests/unit/ -v -m "unit"
\\\

### Solo tests de seguridad
\\\ash
pytest tests/ -v -m "security"
\\\

### Con reporte de cobertura
\\\ash
pytest tests/ --cov=src --cov-report=html
\\\

### Usando script
\\\powershell
.\run_tests.ps1 -Type coverage
\\\

## Escribir Tests

### Estructura Básica
\\\python
import pytest

class TestMiModulo:
    @pytest.mark.unit
    def test_case_simple(self):
        # Arrange
        datos = {"key": "value"}
        
        # Act
        resultado = mi_funcion(datos)
        
        # Assert
        assert resultado == esperado
\\\

### Con Fixtures
\\\python
def test_con_fixture(sample_user_data):
    usuario = create_user(sample_user_data)
    assert usuario.email == sample_user_data["email"]
\\\

## Mocks y Patches

\\\python
from unittest.mock import patch, Mock

@patch('src.services.external_api.call')
def test_con_mock(mock_call):
    mock_call.return_value = {"status": "ok"}
    resultado = mi_funcion()
    mock_call.assert_called_once()
\\\

## Markers Disponibles

- **@pytest.mark.unit** - Tests unitarios
- **@pytest.mark.integration** - Tests de integración
- **@pytest.mark.security** - Tests de seguridad
- **@pytest.mark.slow** - Tests lentos
- **@pytest.mark.e2e** - Tests end-to-end

## Cobertura de Tests

Objetivo: **70% mínimo**

\\\ash
pytest tests/ --cov=src --cov-report=term-missing
\\\

El reporte muestra qué líneas NO están cubiertas.

## Mejores Prácticas

1. ✅ Un assert por test (o use parametrize)
2. ✅ Nombres descriptivos: \	est_should_\*\
3. ✅ Use fixtures para setup compartido
4. ✅ Mock dependencias externas
5. ✅ Test casos felices Y errores
6. ✅ Use factories para datos complejos

## Evitar

1. ❌ Tests que dependen de orden de ejecución
2. ❌ Sleep/wait en tests (usar mock del tiempo)
3. ❌ Tests que modifican archivos del sistema
4. ❌ Tests conectados a bases de datos reales
5. ❌ Tests lentos (> 1 segundo sin razón)

---
Última actualización: 31/05/2026
