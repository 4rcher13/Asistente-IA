# 🔒 Guía de Seguridad - Asistente Ícaro

## ⚠️ Vulnerabilidades Corregidas

### 1. **Secretos Expuestos en Git** [CRÍTICO]
- ✅ **Acción tomada**: `.env` ahora está ignorado por Git
- ✅ **Acción tomada**: Creado `.env.example` como plantilla
- ✅ **Acción tomada**: `.env` actualizado con placeholders

**Por favor revoca los siguientes tokens (fueron expuestos públicamente):**

#### GitHub Token
1. Ve a: https://github.com/settings/tokens
2. Encuentra: `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`
3. Haz clic en **"Delete"** ⚠️

#### Gemini API Key
1. Ve a: https://ai.google.dev/aistudio/apikeys
2. Encuentra: `AIzaSyDQ7K29F1F70GxuS7suwuwXjuMV66b2pK4`
3. Haz clic en la papelera para eliminar ⚠️

#### NVIDIA API Key
1. Ve a: https://build.nvidia.com/account/api-keys
2. Encuentra: `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`
3. Haz clic en **"Delete"** ⚠️

---

## 🔑 Configuración Correcta de Secretos

### Opción 1: Variables de Entorno (Recomendado en Producción)
```bash
# Windows PowerShell
$env:GEMINI_API_KEY="tu_clave_aqui"
$env:GITHUB_TOKEN="tu_token_aqui"
$env:NVIDIA_API_KEY="tu_clave_aqui"
```

### Opción 2: Archivo `.env` Local (Desarrollo)
1. Copia `.env.example` a `.env`
2. Completa con tus credenciales reales
3. **NUNCA** hagas commit de `.env`

```bash
# Linux/Mac
cp .env.example .env
nano .env

# Windows
copy .env.example .env
# Abre en tu editor y completa
```

---

## 📋 Checklist de Seguridad

- [x] `.env` ignorado por Git
- [x] `.env.example` creado como plantilla
- [x] `.gitignore` actualizado con patrones de seguridad
- [x] `.env` limpiado de secretos reales
- [ ] **ACCIÓN REQUERIDA**: Revocar tokens expuestos
- [ ] Generar nuevos tokens después de revocar

---

## 🛡️ Mejores Prácticas

### ✅ DO's (Deberías hacer)
- ✅ Usar `.env.example` para documentar variables requeridas
- ✅ Revisar `.gitignore` antes de cada commit
- ✅ Usar `git status` para verificar qué se va a commitear
- ✅ Rotar credenciales regularmente
- ✅ Usar secretos managers (GitHub Secrets, Azure Key Vault, etc.)

### ❌ DON'Ts (NO deberías hacer)
- ❌ Commitear archivos `.env` a Git
- ❌ Hardcodear credenciales en código
- ❌ Compartir tokens por chat/email
- ❌ Usar la misma credencial en múltiples servicios
- ❌ Dejar expiración de tokens sin vigilancia

---

## 🔍 Cómo Verificar Futuros Cambios

Antes de cada commit, ejecuta:
```bash
# Ver qué se va a commitear
git diff --staged

# Si ves secretos, no comitees
git reset HEAD <archivo>
```

---

## 📚 Referencias

- [GitHub: Managing Your Personal Access Tokens](https://docs.github.com/en/authentication/keeping-your-account-and-data-secure/managing-your-personal-access-tokens)
- [Google AI Studio: API Keys](https://ai.google.dev/aistudio/apikeys)
- [OWASP: Secrets Management](https://cheatsheetseries.owasp.org/cheatsheets/Secrets_Management_Cheat_Sheet.html)

---

**Última actualización**: 2026-05-29  
**Responsable de seguridad**: Copilot Security Scan
