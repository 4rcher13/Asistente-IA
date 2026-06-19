# 🔐 Guía de Seguridad - Asistente IA

## Configuración de Secretos

### 1. Variables de Entorno

Todas las variables sensibles se manejan a través de .env:

\\\ash
# .env (NO versionable - local only)
SECRET_KEY=tu-clave-secreta
DB_PASSWORD=contraseña-bd
API_KEY_OPENAI=sk-...
\\\

### 2. Cargar Configuración

\\\python
from src.config import config

# Usar la configuración en tu app
print(config.SECRET_KEY)
print(config.DATABASE_URL)
\\\

### 3. Validación de Entrada

Usar Pydantic para validar TODA entrada de usuario:

\\\python
from src.schemas import QueryInput, UserCreate

# Validar búsqueda
query = QueryInput(query="user search", limit=10)

# Validar usuario
user = UserCreate(
    email="user@example.com",
    password="SecurePass123!",
    full_name="John Doe"
)
\\\

## Checklist de Seguridad

- [x] Secretos en .env (no versionado)
- [x] Validación con Pydantic
- [x] Type hints en todas las funciones
- [ ] Hashing de contraseñas (bcrypt)
- [ ] JWT para autenticación
- [ ] Rate limiting
- [ ] CORS configurado
- [ ] Headers de seguridad
- [ ] Tests de seguridad

## Próximos Pasos

1. Implementar autenticación JWT
2. Agregar hashing de contraseñas con bcrypt
3. Crear middleware de validación
4. Agregar rate limiting
5. Configurar CORS

---
Última actualización: 30/05/2026
