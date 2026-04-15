# Rendimiento y Optimización en Python

## Regla número 1: Medir antes de optimizar

```python
# Profiling básico con cProfile
import cProfile
import pstats

with cProfile.Profile() as pr:
    mi_funcion_lenta()

stats = pstats.Stats(pr)
stats.sort_stats(pstats.SortKey.TIME)
stats.print_stats(10)  # Top 10 funciones más lentas

# Profiling de línea con line_profiler (pip install line-profiler)
# Agregar decorador @profile y ejecutar: kernprof -l -v script.py
```

## Estructuras de datos correctas

```python
from collections import defaultdict, Counter, deque
import heapq

# ❌ Búsqueda en lista: O(n)
usuarios = [{"id": 1}, {"id": 2}, ...]
usuario = next(u for u in usuarios if u["id"] == target_id)

# ✅ Búsqueda en dict: O(1)
usuarios_por_id = {u["id"]: u for u in usuarios}
usuario = usuarios_por_id[target_id]

# ✅ Contar elementos: Counter es más rápido que dict manual
palabras = texto.split()
frecuencias = Counter(palabras)
top_10 = frecuencias.most_common(10)

# ✅ Cola con prioridades: heapq
cola = []
heapq.heappush(cola, (prioridad, tarea))
siguiente = heapq.heappop(cola)

# ✅ Agregar/quitar del inicio: deque O(1) vs list O(n)
buffer = deque(maxlen=1000)  # Buffer circular automático
buffer.appendleft(nuevo_elemento)
```

## Generadores y lazy evaluation

```python
# ❌ Carga todo en memoria
def procesar_archivo_grande(ruta: str) -> list[str]:
    return [linea.strip() for linea in open(ruta)]  # ¡Todo en RAM!

# ✅ Generador: procesa línea por línea
def procesar_archivo_grande(ruta: str):
    with open(ruta, encoding="utf-8") as f:
        for linea in f:
            yield linea.strip()

# ✅ Expresiones generadoras en lugar de list comprehensions cuando no necesitas lista
suma = sum(x**2 for x in range(1_000_000))  # No crea lista intermedia
```

## Operaciones en paralelo

```python
import asyncio
import concurrent.futures
from typing import Callable, TypeVar

T = TypeVar("T")

# I/O bound: usar asyncio
async def descargar_todos(urls: list[str]) -> list[bytes]:
    import httpx
    async with httpx.AsyncClient() as client:
        tareas = [client.get(url) for url in urls]
        respuestas = await asyncio.gather(*tareas)
        return [r.content for r in respuestas]

# CPU bound: usar ProcessPoolExecutor
def procesar_imagen(ruta: str) -> dict:
    # Operación pesada de CPU
    ...

def procesar_todas_imagenes(rutas: list[str]) -> list[dict]:
    with concurrent.futures.ProcessPoolExecutor() as executor:
        resultados = list(executor.map(procesar_imagen, rutas))
    return resultados

# I/O bound sync (legacy): ThreadPoolExecutor
def consultar_api(url: str) -> dict:
    import requests
    return requests.get(url).json()

def consultar_apis(urls: list[str]) -> list[dict]:
    with concurrent.futures.ThreadPoolExecutor(max_workers=10) as executor:
        return list(executor.map(consultar_api, urls))
```

## Caché para funciones costosas

```python
from functools import lru_cache, cache
import time

# Cache simple (Python 3.9+)
@cache
def fibonacci(n: int) -> int:
    if n < 2:
        return n
    return fibonacci(n - 1) + fibonacci(n - 2)

# Cache con límite de tamaño
@lru_cache(maxsize=128)
def buscar_en_db(user_id: int) -> dict:
    # Costosa consulta a BD
    ...

# Cache con TTL (expiración por tiempo)
import threading

class TTLCache:
    def __init__(self, ttl_segundos: int = 300):
        self._cache: dict = {}
        self._timestamps: dict = {}
        self._ttl = ttl_segundos
        self._lock = threading.Lock()

    def get(self, clave: str):
        with self._lock:
            if clave in self._cache:
                if time.time() - self._timestamps[clave] < self._ttl:
                    return self._cache[clave]
                del self._cache[clave]
                del self._timestamps[clave]
        return None

    def set(self, clave: str, valor) -> None:
        with self._lock:
            self._cache[clave] = valor
            self._timestamps[clave] = time.time()
```

## Numpy para cálculos numéricos

```python
import numpy as np

# ❌ Lento: bucle Python para cálculos numéricos
def promedio_manual(datos: list[float]) -> float:
    return sum(datos) / len(datos)

# ✅ Numpy: operaciones vectorizadas en C
def promedio_numpy(datos: list[float]) -> float:
    return np.mean(datos)

# Para dataframes y análisis: pandas
import pandas as pd

df = pd.read_csv("datos.csv")
resultado = (
    df.groupby("categoria")
      .agg({"valor": ["mean", "sum", "count"]})
      .reset_index()
)
```

## Benchmarking con timeit

```python
import timeit

# Comparar dos implementaciones
tiempo_lista = timeit.timeit(
    "5 in lista",
    setup="lista = list(range(10000))",
    number=10000
)

tiempo_set = timeit.timeit(
    "5 in conjunto",
    setup="conjunto = set(range(10000))",
    number=10000
)

print(f"Lista: {tiempo_lista:.4f}s")
print(f"Set: {tiempo_set:.4f}s")
print(f"Set es {tiempo_lista/tiempo_set:.1f}x más rápido")
```

## Señales de código lento a identificar

- Bucles `for` con operaciones de string concatenation (`+=`) → usar `"".join()`
- Acceso repetido a atributos de objeto en bucle → cachear en variable local
- Operaciones de I/O síncronas donde podrían ser async
- Listas donde se necesitan sets para búsqueda de pertenencia
- Re-compilar regex en cada llamada → compilar una vez con `re.compile()`
