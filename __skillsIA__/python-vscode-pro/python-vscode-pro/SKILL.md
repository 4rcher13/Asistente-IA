---
name: python-vscode-pro
description: >
  Programa en Python de forma profesional, optimizada y segura usando Visual Studio Code y
  sus herramientas integradas. Usa esta skill siempre que el usuario quiera escribir, refactorizar,
  depurar, estructurar o revisar código Python — especialmente si menciona VS Code, extensiones,
  entornos virtuales, type hints, linting, testing, formateo, seguridad de código, rendimiento,
  o quiere llevar su código Python al siguiente nivel de calidad profesional. También activa cuando
  el usuario dice "hazlo más limpio", "quiero buenas prácticas", "cómo estructuro mi proyecto",
  "quiero código seguro", o cualquier variante de querer mejorar código Python existente.
---

# Python Profesional con VS Code

Esta skill guía la escritura, revisión y mejora de código Python siguiendo estándares profesionales de
la industria: código limpio, tipado estático, seguro, bien testeado y optimizado — todo integrado con
el ecosistema de herramientas de VS Code.

---

## Flujo de trabajo al recibir una tarea Python

1. **Analizar el contexto**: ¿Es código nuevo, refactorización, debugging, estructura de proyecto, o revisión de seguridad?
2. **Leer la referencia correcta** según el tipo de tarea (ver tabla abajo)
3. **Aplicar los estándares** del archivo de referencia correspondiente
4. **Incluir siempre** configuración VS Code relevante cuando se cree código o proyectos

### Tabla de referencias

| Tipo de tarea | Archivo a leer |
|---|---|
| Estructura de proyecto, entornos virtuales, dependencias | `references/project-setup.md` |
| Calidad de código: tipos, linting, formateo | `references/code-quality.md` |
| Testing, TDD, cobertura | `references/testing.md` |
| Seguridad, validación de entradas, secretos | `references/security.md` |
| Rendimiento, profiling, optimización | `references/performance.md` |
| Configuración VS Code, extensiones, atajos | `references/vscode-config.md` |

---

## Principios siempre activos (sin necesidad de leer referencias)

### Estilo y claridad
- Seguir **PEP 8** en todo momento
- Nombres en `snake_case` para variables/funciones, `PascalCase` para clases, `UPPER_SNAKE_CASE` para constantes
- Docstrings en todas las funciones públicas (formato Google o NumPy)
- Máximo 79 caracteres por línea (o 88 si el proyecto usa Black)

### Type hints siempre
```python
# ❌ Sin tipos
def procesar(datos, limite):
    ...

# ✅ Con tipos
from typing import Optional
def procesar(datos: list[dict], limite: int = 100) -> Optional[list[dict]]:
    ...
```

### Manejo de errores explícito
```python
# ❌ Captura genérica
try:
    resultado = operacion()
except Exception:
    pass

# ✅ Específico con contexto
try:
    resultado = operacion()
except ValueError as e:
    logger.error("Valor inválido en operacion: %s", e)
    raise
except ConnectionError as e:
    logger.warning("Fallo de conexión, reintentando: %s", e)
    raise RuntimeError("No se pudo completar la operación") from e
```

### Logging en lugar de print
```python
import logging
logger = logging.getLogger(__name__)

# ❌ Para debugging
print(f"procesando: {item}")

# ✅ Logging estructurado
logger.debug("Procesando ítem: %s", item)
```

### Secrets y configuración nunca en código
```python
# ❌ Hardcoded
API_KEY = "sk-abc123..."

# ✅ Variables de entorno
import os
from dotenv import load_dotenv
load_dotenv()
API_KEY = os.getenv("API_KEY")
if not API_KEY:
    raise EnvironmentError("La variable API_KEY no está configurada")
```

---

## Estructura mínima de un proyecto Python profesional

```
mi_proyecto/
├── .vscode/
│   ├── settings.json       # Configuración del workspace
│   └── extensions.json     # Extensiones recomendadas
├── src/
│   └── mi_proyecto/
│       ├── __init__.py
│       ├── main.py
│       └── utils/
├── tests/
│   ├── conftest.py
│   └── test_main.py
├── .env.example            # Variables de entorno (sin valores reales)
├── .gitignore
├── pyproject.toml          # Config central (PEP 518)
├── README.md
└── requirements.txt        # O usa pyproject.toml con extras
```

### `.vscode/settings.json` base
```json
{
  "python.defaultInterpreterPath": "${workspaceFolder}/.venv/bin/python",
  "editor.formatOnSave": true,
  "[python]": {
    "editor.defaultFormatter": "ms-python.black-formatter",
    "editor.codeActionsOnSave": {
      "source.organizeImports": "explicit"
    }
  },
  "python.linting.enabled": true,
  "mypy-type-checker.enabled": true,
  "python.testing.pytestEnabled": true,
  "python.testing.unittestEnabled": false
}
```

### `.vscode/extensions.json` base
```json
{
  "recommendations": [
    "ms-python.python",
    "ms-python.black-formatter",
    "ms-python.isort",
    "ms-python.mypy-type-checker",
    "charliermarsh.ruff",
    "ms-python.debugpy",
    "njpwerner.autodocstring",
    "usernamehw.errorlens",
    "eamodio.gitlens"
  ]
}
```

---

## Configuración `pyproject.toml` estándar

```toml
[build-system]
requires = ["hatchling"]
build-backend = "hatchling.build"

[project]
name = "mi-proyecto"
version = "0.1.0"
requires-python = ">=3.11"
dependencies = []

[project.optional-dependencies]
dev = ["pytest", "pytest-cov", "black", "ruff", "mypy", "python-dotenv"]

[tool.black]
line-length = 88
target-version = ["py311"]

[tool.ruff]
line-length = 88
select = ["E", "W", "F", "I", "N", "B", "UP"]

[tool.mypy]
python_version = "3.11"
strict = true
ignore_missing_imports = true

[tool.pytest.ini_options]
testpaths = ["tests"]
addopts = "--cov=src --cov-report=term-missing"
```

---

## Comandos rápidos de referencia (terminal integrada en VS Code)

```bash
# Crear entorno virtual
python -m venv .venv && source .venv/bin/activate  # Linux/macOS
python -m venv .venv && .venv\Scripts\activate      # Windows

# Instalar dependencias de dev
pip install -e ".[dev]"

# Formatear código
black src/ tests/

# Linting rápido
ruff check src/ --fix

# Verificar tipos
mypy src/

# Ejecutar tests con cobertura
pytest --cov=src --cov-report=html

# Todo junto (pre-commit hook)
black . && ruff check . --fix && mypy src/ && pytest
```

---

## Cuándo leer las referencias detalladas

Lee `references/security.md` si el código involucra:
- Manejo de contraseñas, tokens o datos sensibles
- Validación de entradas de usuario o archivos externos
- Comunicación con APIs externas o bases de datos
- Serialización/deserialización (JSON, pickle, YAML)

Lee `references/performance.md` si el código involucra:
- Procesamiento de grandes volúmenes de datos
- Operaciones I/O intensivas
- Cálculos numéricos o científicos
- Código que debe ejecutarse en tiempo real o near-real-time

Lee `references/testing.md` para:
- Crear suites de tests completas
- Configurar mocks y fixtures
- Implementar TDD desde cero
- Medir y mejorar cobertura
