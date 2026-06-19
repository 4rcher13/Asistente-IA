Configuración de Proyectos Python: Entornos y Dependencias

## Crear un proyecto desde cero

```bash
# 1. Crear directorio del proyecto
mkdir mi_proyecto && cd mi_proyecto

# 2. Inicializar git
git init && git branch -M main

# 3. Crear entorno virtual (siempre dentro del proyecto)
python -m venv .venv

# 4. Activar entorno virtual
source .venv/bin/activate      # Linux/macOS
.venv\Scripts\activate          # Windows PowerShell
.venv\Scripts\activate.bat      # Windows CMD

# 5. Actualizar pip
pip install --upgrade pip

# 6. Instalar herramientas de desarrollo
pip install black ruff mypy pytest pytest-cov python-dotenv

# 7. Abrir VS Code (detectará el .venv automáticamente)
code .
```

## .gitignore mínimo para Python

```gitignore
# Entorno virtual
.venv/
env/
venv/

# Bytecode
__pycache__/
*.py[cod]
*.pyo

# Distribución
dist/
build/
*.egg-info/

# Testing y cobertura
.pytest_cache/
htmlcov/
.coverage
coverage.xml

# Variables de entorno (NUNCA en git)
.env
.env.local
.env.*.local

# VS Code (workspace personal, no compartir)
.vscode/settings.json
# Sí compartir:
# .vscode/extensions.json
# .vscode/launch.json

# macOS
.DS_Store

# Mypy
.mypy_cache/

# Ruff
.ruff_cache/
```

## Gestión de dependencias con pyproject.toml

```toml
[project]
name = "mi-proyecto"
version = "0.1.0"
description = "Descripción breve del proyecto"
readme = "README.md"
requires-python = ">=3.11"
license = {text = "MIT"}

# Dependencias de producción
dependencies = [
    "httpx>=0.27",
    "pydantic>=2.0",
    "python-dotenv>=1.0",
]

# Dependencias de desarrollo (instalar con: pip install -e ".[dev]")
[project.optional-dependencies]
dev = [
    "pytest>=8.0",
    "pytest-cov>=5.0",
    "pytest-asyncio>=0.23",
    "black>=24.0",
    "ruff>=0.4",
    "mypy>=1.10",
    "httpx",  # Para tests de API
]

[build-system]
requires = ["hatchling"]
build-backend = "hatchling.build"
```

## Alternativa: uv (reemplazante moderno de pip)

```bash
# Instalar uv (más rápido que pip)
curl -LsSf https://astral.sh/uv/install.sh | sh

# Crear proyecto con uv
uv init mi_proyecto && cd mi_proyecto

# Crear y activar entorno virtual
uv venv && source .venv/bin/activate

# Agregar dependencias
uv add httpx pydantic
uv add --dev pytest black ruff mypy

# Instalar todas las dependencias del proyecto
uv sync

# Ejecutar comandos en el entorno
uv run python main.py
uv run pytest
```

## Estructura de proyecto según tipo

### Script simple
```
mi_script/
├── .venv/
├── .env
├── main.py
├── requirements.txt
└── .gitignore
```

### Aplicación mediana
```
mi_app/
├── .venv/
├── .vscode/
│   ├── extensions.json
│   └── launch.json
├── src/
│   └── mi_app/
│       ├── __init__.py
│       ├── main.py
│       ├── config.py
│       ├── models/
│       └── services/
├── tests/
│   └── conftest.py
├── .env.example
├── .gitignore
├── pyproject.toml
└── README.md
```

### API con FastAPI
```
mi_api/
├── .venv/
├── src/
│   └── mi_api/
│       ├── __init__.py
│       ├── main.py          # FastAPI app
│       ├── config.py        # Settings con pydantic-settings
│       ├── routers/
│       │   ├── usuarios.py
│       │   └── productos.py
│       ├── models/          # Modelos SQLAlchemy
│       ├── schemas/         # Schemas Pydantic
│       ├── services/        # Lógica de negocio
│       └── dependencies.py  # Inyección de dependencias
├── tests/
├── alembic/                 # Migraciones DB
├── Dockerfile
├── docker-compose.yml
├── .env.example
└── pyproject.toml
```

## Verificar entorno activo en VS Code

1. Ver en la barra inferior de VS Code (esquina inferior izquierda)
2. Debe mostrar la versión de Python de `.venv`
3. Si no está activo: `Ctrl+Shift+P` → "Python: Select Interpreter" → elegir `./.venv/bin/python`

## requirements.txt vs pyproject.toml

| Característica | requirements.txt | pyproject.toml |
|---|---|---|
| Estándar moderno | ❌ Legacy | ✅ PEP 518/621 |
| Dependencias de dev | Manual (requirements-dev.txt) | `[optional-dependencies]` |
| Metadatos del proyecto | ❌ | ✅ |
| Herramientas de build | ❌ | ✅ |
| Recomendación | Solo si obligado | **Usar siempre** |

Generar requirements.txt desde pyproject.toml si se necesita:
```bash
pip freeze > requirements.txt
# O más limpio:
pip list --format=freeze > requirements.txt
```
