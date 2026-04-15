# Seguridad en Python: Guía de Referencia

## Regla de oro: Nunca confiar en datos externos

Todo input del usuario, archivos, APIs externas y variables de entorno debe ser validado antes de usar.

## Manejo seguro de contraseñas y secrets

```python
# ❌ NUNCA guardar contraseñas en texto plano
PASSWORD = "mi_contrasena_123"

# ✅ Usar bcrypt o argon2 para hashear contraseñas
import bcrypt

def hashear_contrasena(contrasena: str) -> bytes:
    salt = bcrypt.gensalt(rounds=12)  # 12 rounds = balance seguridad/velocidad
    return bcrypt.hashpw(contrasena.encode("utf-8"), salt)

def verificar_contrasena(contrasena: str, hash_guardado: bytes) -> bool:
    return bcrypt.checkpw(contrasena.encode("utf-8"), hash_guardado)

# ✅ Usar secrets para tokens seguros (no random)
import secrets
token = secrets.token_urlsafe(32)  # 32 bytes = 256 bits de entropía
```

## Variables de entorno con validación

```python
from dotenv import load_dotenv
import os

load_dotenv()

def requerir_env(nombre: str) -> str:
    """Obtiene variable de entorno o falla con mensaje claro."""
    valor = os.getenv(nombre)
    if not valor:
        raise EnvironmentError(
            f"Variable de entorno requerida no encontrada: '{nombre}'. "
            f"Revisa tu archivo .env o configuración del sistema."
        )
    return valor

# Uso
DATABASE_URL = requerir_env("DATABASE_URL")
API_KEY = requerir_env("API_KEY")
```

## Validación de entradas con Pydantic

```python
from pydantic import BaseModel, EmailStr, field_validator, model_validator
from typing import Annotated
from pydantic import Field

class CrearUsuario(BaseModel):
    nombre: Annotated[str, Field(min_length=2, max_length=100)]
    email: EmailStr
    edad: Annotated[int, Field(ge=0, le=150)]
    contrasena: Annotated[str, Field(min_length=8)]

    @field_validator("nombre")
    @classmethod
    def nombre_valido(cls, v: str) -> str:
        if not v.replace(" ", "").isalpha():
            raise ValueError("El nombre solo puede contener letras y espacios")
        return v.strip().title()

    @field_validator("contrasena")
    @classmethod
    def contrasena_fuerte(cls, v: str) -> str:
        if not any(c.isupper() for c in v):
            raise ValueError("La contraseña debe tener al menos una mayúscula")
        if not any(c.isdigit() for c in v):
            raise ValueError("La contraseña debe tener al menos un número")
        return v

# Uso
try:
    usuario = CrearUsuario(
        nombre="Juan Pérez",
        email="juan@example.com",
        edad=30,
        contrasena="Segura123"
    )
except ValueError as e:
    print(f"Validación fallida: {e}")
```

## Consultas SQL seguras (evitar SQL Injection)

```python
import sqlite3

# ❌ VULNERABLE a SQL Injection
def buscar_usuario_inseguro(nombre: str):
    conn = sqlite3.connect("db.sqlite")
    query = f"SELECT * FROM usuarios WHERE nombre = '{nombre}'"  # ¡PELIGRO!
    return conn.execute(query).fetchall()

# ✅ Usar parámetros preparados siempre
def buscar_usuario(nombre: str) -> list:
    conn = sqlite3.connect("db.sqlite")
    query = "SELECT * FROM usuarios WHERE nombre = ?"
    return conn.execute(query, (nombre,)).fetchall()

# ✅ Con SQLAlchemy ORM (recomendado)
from sqlalchemy import select
from sqlalchemy.orm import Session

def buscar_usuario_orm(session: Session, nombre: str) -> list:
    stmt = select(Usuario).where(Usuario.nombre == nombre)
    return session.scalars(stmt).all()
```

## Deserialización segura

```python
import json
import yaml

# ❌ NUNCA usar pickle con datos externos (permite ejecución de código arbitrario)
import pickle
datos = pickle.loads(datos_externos)  # ¡CRÍTICO: NO HACER!

# ✅ JSON es seguro para datos externos
datos = json.loads(texto_json)  # OK

# ⚠️ yaml.load() es peligroso, usar yaml.safe_load()
# ❌
datos = yaml.load(contenido)  # Ejecuta código Python arbitrario
# ✅
datos = yaml.safe_load(contenido)  # Solo tipos básicos

# ✅ Para formatos desconocidos, usar pydantic para validar después de parsear
from pydantic import BaseModel
class MiModelo(BaseModel):
    campo: str
    valor: int

modelo = MiModelo.model_validate(datos)  # Valida tipos y estructura
```

## Manejo seguro de archivos y rutas

```python
from pathlib import Path

# ❌ Path traversal vulnerability
def leer_archivo_inseguro(nombre_archivo: str) -> str:
    ruta = f"/datos/usuarios/{nombre_archivo}"
    return open(ruta).read()  # Un atacante puede usar "../../etc/passwd"

# ✅ Validar que la ruta esté dentro del directorio permitido
def leer_archivo(nombre_archivo: str) -> str:
    directorio_base = Path("/datos/usuarios").resolve()
    ruta = (directorio_base / nombre_archivo).resolve()

    # Verificar que la ruta resuelta siga dentro del directorio permitido
    if not str(ruta).startswith(str(directorio_base)):
        raise PermissionError(f"Acceso denegado: ruta fuera del directorio permitido")

    return ruta.read_text(encoding="utf-8")
```

## Rate limiting y protección contra fuerza bruta

```python
import time
from collections import defaultdict
from threading import Lock

class RateLimiter:
    """Limita intentos por IP o usuario."""

    def __init__(self, max_intentos: int = 5, ventana_segundos: int = 60):
        self.max_intentos = max_intentos
        self.ventana = ventana_segundos
        self._intentos: dict[str, list[float]] = defaultdict(list)
        self._lock = Lock()

    def verificar(self, clave: str) -> bool:
        """Retorna True si el intento está permitido, False si bloqueado."""
        ahora = time.time()
        with self._lock:
            # Limpiar intentos fuera de la ventana temporal
            self._intentos[clave] = [
                t for t in self._intentos[clave]
                if ahora - t < self.ventana
            ]
            if len(self._intentos[clave]) >= self.max_intentos:
                return False
            self._intentos[clave].append(ahora)
            return True

limiter = RateLimiter()

def login(usuario: str, contrasena: str, ip: str) -> bool:
    if not limiter.verificar(ip):
        raise PermissionError("Demasiados intentos. Espera antes de reintentar.")
    # ... lógica de autenticación
```

## Checklist de seguridad

Antes de considerar código "listo":

- [ ] ¿Las entradas de usuario están validadas con Pydantic o similar?
- [ ] ¿Las contraseñas usan bcrypt/argon2 (no md5/sha1 directos)?
- [ ] ¿Los secrets están en variables de entorno (no hardcoded)?
- [ ] ¿Las consultas SQL usan parámetros preparados?
- [ ] ¿Se evita `pickle`, `eval`, `exec` con datos externos?
- [ ] ¿Se usa `yaml.safe_load()` en lugar de `yaml.load()`?
- [ ] ¿Las rutas de archivos están validadas para evitar path traversal?
- [ ] ¿Ruff con reglas `S` (bandit) está activo y pasa sin errores?
