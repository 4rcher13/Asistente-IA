# VS Code para Python: Configuración Completa y Extensiones

## Extensiones esenciales

| ID de extensión | Función |
|---|---|
| `ms-python.python` | Soporte Python base (IntelliSense, debugging, entornos) |
| `ms-python.black-formatter` | Formateo automático con Black |
| `ms-python.isort` | Ordenar imports automáticamente |
| `ms-python.mypy-type-checker` | Verificación de tipos en tiempo real |
| `charliermarsh.ruff` | Linting ultrarrápido (reemplaza flake8) |
| `ms-python.debugpy` | Depurador Python avanzado |
| `njpwerner.autodocstring` | Generar docstrings con un atajo |
| `usernamehw.errorlens` | Mostrar errores inline en el editor |
| `eamodio.gitlens` | Git avanzado con blame inline |
| `ms-python.vscode-pylance` | Servidor de lenguaje rápido (Pylance) |

Instalar todas de golpe desde terminal integrada:
```bash
code --install-extension ms-python.python ms-python.black-formatter \
     ms-python.isort ms-python.mypy-type-checker charliermarsh.ruff \
     ms-python.debugpy njpwerner.autodocstring usernamehw.errorlens \
     eamodio.gitlens ms-python.vscode-pylance
```

## settings.json completo para Python

```json
{
  // === Intérprete Python ===
  "python.defaultInterpreterPath": "${workspaceFolder}/.venv/bin/python",

  // === Formateo automático ===
  "editor.formatOnSave": true,
  "[python]": {
    "editor.defaultFormatter": "ms-python.black-formatter",
    "editor.codeActionsOnSave": {
      "source.organizeImports": "explicit"
    },
    "editor.rulers": [88]
  },

  // === Linting ===
  "ruff.enable": true,
  "ruff.fixAll": true,
  "ruff.organizeImports": true,

  // === Type checking ===
  "python.analysis.typeCheckingMode": "strict",
  "mypy-type-checker.args": ["--strict"],

  // === Testing ===
  "python.testing.pytestEnabled": true,
  "python.testing.unittestEnabled": false,
  "python.testing.pytestArgs": ["tests", "-v"],
  "python.testing.autoTestDiscoverOnSaveEnabled": true,

  // === Editor general ===
  "editor.tabSize": 4,
  "editor.insertSpaces": true,
  "editor.trimAutoWhitespace": true,
  "files.trimTrailingWhitespace": true,
  "files.insertFinalNewline": true,

  // === IntelliSense ===
  "python.analysis.autoImportCompletions": true,
  "python.analysis.indexing": true,

  // === Terminal integrada ===
  "python.terminal.activateEnvironment": true,
  "terminal.integrated.defaultProfile.linux": "bash",
  "terminal.integrated.defaultProfile.windows": "PowerShell"
}
```

## launch.json para debugging

```json
{
  "version": "0.2.0",
  "configurations": [
    {
      "name": "Python: Archivo actual",
      "type": "debugpy",
      "request": "launch",
      "program": "${file}",
      "console": "integratedTerminal",
      "envFile": "${workspaceFolder}/.env"
    },
    {
      "name": "Python: Módulo",
      "type": "debugpy",
      "request": "launch",
      "module": "mi_proyecto.main",
      "console": "integratedTerminal",
      "envFile": "${workspaceFolder}/.env"
    },
    {
      "name": "Python: Tests (pytest)",
      "type": "debugpy",
      "request": "launch",
      "module": "pytest",
      "args": ["${file}", "-v"],
      "console": "integratedTerminal"
    },
    {
      "name": "FastAPI: Servidor de desarrollo",
      "type": "debugpy",
      "request": "launch",
      "module": "uvicorn",
      "args": [
        "mi_proyecto.app:app",
        "--reload",
        "--host", "0.0.0.0",
        "--port", "8000"
      ],
      "console": "integratedTerminal",
      "envFile": "${workspaceFolder}/.env"
    }
  ]
}
```

## Atajos de teclado útiles (VS Code)

| Atajo | Acción |
|---|---|
| `F5` | Iniciar debugging |
| `F9` | Toggle breakpoint |
| `F10` | Step over |
| `F11` | Step into |
| `Shift+F11` | Step out |
| `Ctrl+Shift+P` | Paleta de comandos |
| `Ctrl+Shift+\`` | Nueva terminal |
| `Ctrl+.` | Quick fixes / refactors |
| `F2` | Renombrar símbolo (refactor) |
| `Ctrl+Shift+I` | Formatear documento |
| `Alt+Shift+F` | Organizar imports |
| `Ctrl+Shift+T` | Abrir Testing Explorer |

## Tareas automatizadas con tasks.json

```json
{
  "version": "2.0.0",
  "tasks": [
    {
      "label": "Lint + Format + Types",
      "type": "shell",
      "command": "black . && ruff check . --fix && mypy src/",
      "group": "build",
      "presentation": { "reveal": "always" }
    },
    {
      "label": "Tests con cobertura",
      "type": "shell",
      "command": "pytest --cov=src --cov-report=html && open htmlcov/index.html",
      "group": "test"
    },
    {
      "label": "Crear entorno virtual",
      "type": "shell",
      "command": "python -m venv .venv && .venv/bin/pip install -e '.[dev]'",
      "group": "build"
    }
  ]
}
```

Ejecutar tareas: `Ctrl+Shift+P` → "Tasks: Run Task"

## Snippets útiles para Python

Agregar a `.vscode/python.code-snippets`:

```json
{
  "Dataclass": {
    "prefix": "dc",
    "body": [
      "from dataclasses import dataclass, field",
      "",
      "@dataclass",
      "class ${1:NombreClase}:",
      "    ${2:campo}: ${3:str}",
      "    $0"
    ]
  },
  "Logger": {
    "prefix": "log",
    "body": [
      "import logging",
      "logger = logging.getLogger(__name__)"
    ]
  },
  "Type hint function": {
    "prefix": "def",
    "body": [
      "def ${1:nombre}(${2:param}: ${3:type}) -> ${4:None}:",
      "    \"\"\"${5:Descripción.}\"\"\"",
      "    $0"
    ]
  }
}
```
