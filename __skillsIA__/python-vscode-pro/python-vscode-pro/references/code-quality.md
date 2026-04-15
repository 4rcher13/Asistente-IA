# Calidad de Código Python: Tipos, Linting y Formateo

## Type Hints avanzados (Python 3.10+)

```python
# Tipos básicos modernos (sin importar typing para lo común)
def suma(a: int, b: int) -> int: ...
def nombre(s: str | None = None) -> str: ...

# Colecciones (Python 3.9+ usa minúsculas)
def procesar(items: list[int], mapa: dict[str, float]) -> tuple[int, ...]: ...

# TypedDict para diccionarios con estructura fija
from typing import TypedDict

class Usuario(TypedDict):
    id: int
    nombre: str
    email: str
    activo: bool

# Protocols para duck typing (mejor que ABCs para interfaces simples)
from typing import Protocol

class Serializable(Protocol):
    def to_dict(self) -> dict: ...
    def to_json(self) -> str: ...

# dataclasses para datos estructurados (en lugar de dicts o namedtuples)
from dataclasses import dataclass, field

@dataclass(frozen=True)  # Inmutable
class Config:
    host: str
    puerto: int = 8080
    etiquetas: list[str] = field(default_factory=list)

# Generic para funciones reutilizables
from typing import TypeVar, Generic

T = TypeVar("T")

def primero(items: list[T]) -> T | None:
    return items[0] if items else None
```

## Patrones de Linting con Ruff

Ruff reemplaza flake8 + isort + pyupgrade + muchos más. Configuración recomendada:

```toml
# pyproject.toml
[tool.ruff]
line-length = 88
target-version = "py311"

[tool.ruff.lint]
select = [
    "E",   # pycodestyle errors
    "W",   # pycodestyle warnings
    "F",   # pyflakes
    "I",   # isort
    "N",   # pep8-naming
    "B",   # flake8-bugbear (patrones problemáticos)
    "UP",  # pyupgrade (modernizar sintaxis)
    "S",   # bandit (seguridad básica)
    "C4",  # flake8-comprehensions (list/dict comprensiones)
    "SIM", # flake8-simplify
]
ignore = ["E501"]  # Black maneja la longitud de líneas

[tool.ruff.lint.per-file-ignores]
"tests/**" = ["S101"]  # Permitir assert en tests
```

## Formateo consistente con Black

```toml
[tool.black]
line-length = 88
target-version = ["py311"]
include = '\.pyi?$'
```

Black es no-configurable por diseño. Solo ajustar `line-length`.

## Mypy en modo estricto

```toml
[tool.mypy]
python_version = "3.11"
strict = true
# strict habilita: disallow_any_generics, disallow_untyped_defs,
# warn_return_any, warn_unused_ignores, etc.

# Para librerías sin stubs de tipos:
[[tool.mypy.overrides]]
module = ["libreria_sin_tipos.*"]
ignore_missing_imports = true
```

## Pre-commit hooks

Instalar: `pip install pre-commit && pre-commit install`

```yaml
# .pre-commit-config.yaml
repos:
  - repo: https://github.com/astral-sh/ruff-pre-commit
    rev: v0.4.4
    hooks:
      - id: ruff
        args: [--fix]
      - id: ruff-format

  - repo: https://github.com/pre-commit/mirrors-mypy
    rev: v1.10.0
    hooks:
      - id: mypy
        additional_dependencies: [types-all]
```

## Patrones a evitar (detectados por linters)

```python
# ❌ Mutable default argument
def agregar(item, lista=[]):  # BUG: lista compartida entre llamadas
    lista.append(item)
    return lista

# ✅
def agregar(item, lista=None):
    if lista is None:
        lista = []
    lista.append(item)
    return lista

# ❌ Comparación con None usando ==
if x == None: ...

# ✅
if x is None: ...

# ❌ Bare except
try: ...
except: ...  # Captura hasta SystemExit y KeyboardInterrupt

# ✅
try: ...
except Exception as e: ...

# ❌ f-string sin uso real
nombre = f"{'texto'}"  # innecesario

# ❌ List comprehension innecesaria
lista = [x for x in range(10)]  # usar list(range(10))
cualquiera = any([condicion(x) for x in items])  # usar any(condicion(x) for x in items)
```

## Documentación de funciones (AutoDocstring en VS Code)

Extensión recomendada: `njpwerner.autodocstring` (genera el esqueleto automáticamente).

```python
def calcular_imc(peso_kg: float, altura_m: float) -> float:
    """Calcula el Índice de Masa Corporal (IMC).

    Args:
        peso_kg: Peso de la persona en kilogramos. Debe ser positivo.
        altura_m: Altura de la persona en metros. Debe ser positivo.

    Returns:
        El valor del IMC como número flotante.

    Raises:
        ValueError: Si peso_kg o altura_m son menores o iguales a cero.

    Example:
        >>> calcular_imc(70.0, 1.75)
        22.857142857142858
    """
    if peso_kg <= 0 or altura_m <= 0:
        raise ValueError(f"Valores inválidos: peso={peso_kg}, altura={altura_m}")
    return peso_kg / (altura_m ** 2)
```
