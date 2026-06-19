"""
Script de prueba para validar la configuración de seguridad
Ejecutar: python test_security_setup.py
"""

import sys
from pathlib import Path

# Agregar src al path
sys.path.insert(0, str(Path(__file__).parent))

print("="*60)
print("🔐 VALIDANDO CONFIGURACIÓN DE SEGURIDAD")
print("="*60)

# 1. Verificar .env
print("\n1️⃣ Verificando .env...")
env_file = Path(".env")
if env_file.exists():
    print("   ✅ .env existe")
else:
    print("   ⚠️ .env no encontrado")

# 2. Verificar .env.example
print("\n2️⃣ Verificando .env.example...")
env_example = Path(".env.example")
if env_example.exists():
    print("   ✅ .env.example existe")
else:
    print("   ❌ .env.example no encontrado")

# 3. Verificar .gitignore
print("\n3️⃣ Verificando .gitignore...")
gitignore = Path(".gitignore")
if gitignore.exists():
    content = gitignore.read_text()
    if ".env" in content:
        print("   ✅ .env está en .gitignore")
    else:
        print("   ❌ .env NO está en .gitignore")
else:
    print("   ⚠️ .gitignore no encontrado")

# 4. Verificar config.py
print("\n4️⃣ Verificando config.py...")
from src.config import config
print(f"   ✅ config.py cargado")
print(f"   - Ambiente: {config.ENVIRONMENT}")
print(f"   - Debug: {config.DEBUG}")
print(f"   - BD: {config.DB_HOST}:{config.DB_PORT}/{config.DB_NAME}")

# 5. Verificar Pydantic
print("\n5️⃣ Verificando esquemas de validación...")
try:
    from src.schemas import UserCreate, QueryInput, CommandInput
    print("   ✅ Esquemas importados correctamente")
except ImportError as e:
    print(f"   ❌ Error importando esquemas: {e}")

# 6. Prueba de validación
print("\n6️⃣ Probando validación de entrada...")
try:
    from src.schemas import QueryInput
    
    # Caso válido
    valid_query = QueryInput(query="test search", limit=5)
    print("   ✅ Query válida aceptada")
    
    # Caso inválido
    try:
        invalid_query = QueryInput(query="test; DROP TABLE users")
        print("   ❌ Query peligrosa NO fue bloqueada")
    except ValueError as e:
        print(f"   ✅ Query peligrosa bloqueada: {e}")
        
except Exception as e:
    print(f"   ❌ Error en validación: {e}")

print("\n" + "="*60)
print("✅ VALIDACIÓN COMPLETADA")
print("="*60)
