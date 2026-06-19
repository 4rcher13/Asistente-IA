# Testing en Python: Pytest, Mocks y Cobertura

## Estructura de tests

```
tests/
├── conftest.py          # Fixtures compartidos
├── unit/
│   ├── test_utils.py
│   └── test_models.py
├── integration/
│   └── test_api.py
└── e2e/
    └── test_flujos.py
```

## Anatomía de un buen test (patrón AAA)

```python
import pytest
from mi_proyecto.calculadora import Calculadora

class TestCalculadora:
    def test_suma_positivos(self):
        # Arrange (preparar)
        calc = Calculadora()

        # Act (actuar)
        resultado = calc.sumar(2, 3)

        # Assert (verificar)
        assert resultado == 5

    def test_division_por_cero_lanza_error(self):
        calc = Calculadora()
        with pytest.raises(ZeroDivisionError, match="No se puede dividir por cero"):
            calc.dividir(10, 0)

    @pytest.mark.parametrize("a,b,esperado", [
        (2, 3, 5),
        (-1, 1, 0),
        (0, 0, 0),
        (100, -50, 50),
    ])
    def test_suma_parametrizada(self, a: int, b: int, esperado: int):
        calc = Calculadora()
        assert calc.sumar(a, b) == esperado
```

## Fixtures en conftest.py

```python
# tests/conftest.py
import pytest
from unittest.mock import AsyncMock, MagicMock

@pytest.fixture
def usuario_base():
    """Usuario de prueba reutilizable."""
    return {"id": 1, "nombre": "Test User", "email": "test@example.com"}

@pytest.fixture
def mock_db():
    """Mock de base de datos."""
    db = MagicMock()
    db.query.return_value = []
    return db

@pytest.fixture
async def cliente_http():
    """Cliente HTTP para tests de integración."""
    import httpx
    from mi_proyecto.app import crear_app
    app = crear_app()
    async with httpx.AsyncClient(app=app, base_url="http://test") as client:
        yield client

@pytest.fixture(autouse=True)
def limpiar_env(monkeypatch):
    """Asegura que las variables de entorno no contaminen tests."""
    monkeypatch.setenv("ENV", "test")
    monkeypatch.delenv("API_KEY", raising=False)
```

## Mocking efectivo

```python
from unittest.mock import patch, MagicMock, AsyncMock, call

# Mock de función externa
def test_enviar_email_llama_api():
    with patch("mi_proyecto.notificaciones.smtp_client") as mock_smtp:
        mock_smtp.send.return_value = {"status": "ok"}
        resultado = enviar_email("test@example.com", "Hola")

        mock_smtp.send.assert_called_once()
        args = mock_smtp.send.call_args
        assert args.kwargs["destinatario"] == "test@example.com"

# Mock de módulo completo
@patch("mi_proyecto.servicios.requests.get")
def test_obtener_datos_externos(mock_get):
    mock_get.return_value.json.return_value = {"datos": [1, 2, 3]}
    mock_get.return_value.status_code = 200

    resultado = obtener_datos("https://api.ejemplo.com/datos")

    assert resultado == [1, 2, 3]
    mock_get.assert_called_once_with("https://api.ejemplo.com/datos", timeout=10)

# Mock asíncrono
@pytest.mark.asyncio
async def test_servicio_async():
    mock_repo = AsyncMock()
    mock_repo.buscar_por_id.return_value = {"id": 1, "nombre": "Test"}

    servicio = MiServicio(repositorio=mock_repo)
    resultado = await servicio.obtener_usuario(1)

    assert resultado["nombre"] == "Test"
    mock_repo.buscar_por_id.assert_awaited_once_with(1)
```

## Cobertura de código

```toml
# pyproject.toml
[tool.pytest.ini_options]
testpaths = ["tests"]
addopts = [
    "--cov=src",
    "--cov-report=term-missing",
    "--cov-report=html:htmlcov",
    "--cov-fail-under=80",  # Falla si cobertura < 80%
    "-v",
]

[tool.coverage.run]
omit = ["*/migrations/*", "*/conftest.py", "*/settings*.py"]

[tool.coverage.report]
exclude_lines = [
    "pragma: no cover",
    "if TYPE_CHECKING:",
    "raise NotImplementedError",
    "if __name__ == .__main__.:",
]
```

Comandos útiles:
```bash
pytest                              # Todos los tests
pytest tests/unit/                  # Solo unitarios
pytest -k "test_suma"               # Tests que coincidan con el nombre
pytest --lf                         # Solo los que fallaron la última vez
pytest -x                           # Parar al primer fallo
pytest --cov=src --cov-report=html  # Cobertura con reporte HTML
```

## Integración con VS Code

En `.vscode/settings.json`:
```json
{
  "python.testing.pytestEnabled": true,
  "python.testing.pytestArgs": ["tests", "-v"],
  "python.testing.autoTestDiscoverOnSaveEnabled": true
}
```

Con estas configuraciones, VS Code descubrirá y mostrará los tests en el **Testing Explorer** (ícono de tubo de ensayo en la barra lateral). Puedes:
- Ejecutar tests individuales con click
- Ver cobertura línea por línea con la extensión **Coverage Gutters**
- Depurar tests directamente con breakpoints

## Niveles de testing recomendados

| Tipo | Proporción | Foco |
|---|---|---|
| Unit tests | ~70% | Funciones y clases aisladas con mocks |
| Integration tests | ~20% | Módulos interactuando, DB en memoria |
| E2E tests | ~10% | Flujos completos de usuario |
