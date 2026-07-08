# Security Scan Script - Asistente IA
# Detecta vulnerabilidades OWASP Top 10

Write-Host "=====================================" -ForegroundColor Cyan
Write-Host "🔐 ESCANEO DE SEGURIDAD - FASE 1" -ForegroundColor Cyan
Write-Host "=====================================" -ForegroundColor Cyan

# Directorios existentes
$paths = @()
foreach ($p in @("src", "ui")) {
    if (Test-Path $p) {
        $paths += $p
    }
}

# Validar si existen rutas válidas para analizar
if ($paths.Count -eq 0) {
    Write-Host "❌ No se encontraron los directorios esperados ('src', 'ui')." -ForegroundColor Red
    Write-Host "=====================================" -ForegroundColor Cyan
    exit
}

# Obtener archivos Python una sola vez para evitar búsquedas repetidas
$allPyFiles = Get-ChildItem -Path $paths -Filter "*.py" -Recurse -File -ErrorAction SilentlyContinue

if (-not $allPyFiles) {
    Write-Host "⚠️ No se encontraron archivos Python (*.py) en las rutas especificadas." -ForegroundColor Yellow
    Write-Host "=====================================" -ForegroundColor Cyan
    exit
}

# 1. Buscar archivos Python
Write-Host "`n1️⃣ Identificando archivos Python..." -ForegroundColor Yellow
Write-Host "Encontrados: $($allPyFiles.Count) archivos Python" -ForegroundColor Green

# 2. Buscar hardcoded secrets
Write-Host "`n2️⃣ Buscando secretos hardcodeados..." -ForegroundColor Yellow

$secret_patterns = @(
    "password\s*=\s*['""]",
    "api_key\s*=\s*['""]",
    "secret\s*=\s*['""]",
    "token\s*=\s*['""]",
    "APIKEY",
    "API_KEY",
    "aws_access_key",
    "aws_secret_key",
    "-----BEGIN PRIVATE KEY-----"
)

$found_secrets = 0

foreach ($pattern in $secret_patterns) {
    $matches = $allPyFiles | Select-String -Pattern $pattern -ErrorAction SilentlyContinue

    if ($matches) {
        Write-Host "   ⚠️ Encontrado patrón sospechoso: $pattern" -ForegroundColor Yellow
        # Muestra TODOS los archivos y líneas sin truncar
        foreach ($match in $matches) {
            Write-Host "      $($match.Path):$($match.LineNumber)" -ForegroundColor DarkYellow
        }
        $found_secrets += $matches.Count
    }
}

if ($found_secrets -eq 0) {
    Write-Host "   ✅ Sin secretos hardcodeados detectados" -ForegroundColor Green
} else {
    Write-Host "   ⚠️ Se encontraron $found_secrets potenciales secretos en total" -ForegroundColor Red
}

# 3. Buscar SQL Injection
Write-Host "`n3️⃣ Buscando vulnerabilidades de SQL Injection..." -ForegroundColor Yellow

$sql_patterns = @(
    'execute\([^)]*\+',
    'query\([^)]*\+',
    'sql\s*=\s*.+',
    '\.format\(.*sql'
)

$sql_vulns = 0

foreach ($pattern in $sql_patterns) {
    $matches = $allPyFiles | Select-String -Pattern $pattern -ErrorAction SilentlyContinue

    if ($matches) {
        Write-Host "   ⚠️ Posible SQL Injection: $pattern" -ForegroundColor Red
        foreach ($match in $matches) {
            Write-Host "      $($match.Path):$($match.LineNumber) -> $($match.Line.Trim())" -ForegroundColor DarkYellow
        }
        $sql_vulns += $matches.Count
    }
}

if ($sql_vulns -eq 0) {
    Write-Host "   ✅ Sin vulnerabilidades SQL Injection obvias" -ForegroundColor Green
}

# 4. Buscar Command Injection
Write-Host "`n4️⃣ Buscando Command Injection vulnerabilities..." -ForegroundColor Yellow

$cmd_patterns = @(
    'os\.system\([^)]*',
    'os\.popen\([^)]*',
    'subprocess\.call\([^)]*',
    'shell\s*=\s*True'
)

$cmd_vulns = 0

foreach ($pattern in $cmd_patterns) {
    $matches = $allPyFiles | Select-String -Pattern $pattern -ErrorAction SilentlyContinue

    if ($matches) {
        Write-Host "   ⚠️ Uso peligroso detectado: $pattern" -ForegroundColor Yellow
        foreach ($match in $matches) {
            Write-Host "      $($match.Path):$($match.LineNumber)" -ForegroundColor DarkYellow
        }
        $cmd_vulns += $matches.Count
    }
}

if ($cmd_vulns -eq 0) {
    Write-Host "   ✅ Sin Command Injection detectado" -ForegroundColor Green
} else {
    Write-Host "   ⚠️ Se encontraron $cmd_vulns instancias de riesgo" -ForegroundColor Yellow
}

# 5. Buscar XSS
Write-Host "`n5️⃣ Buscando XSS vulnerabilities..." -ForegroundColor Yellow

$xss_patterns = @(
    'innerHTML\s*=',
    "html\s*=\s*f['""]",
    'format\s*\('
)

$xss_vulns = 0

foreach ($pattern in $xss_patterns) {
    $matches = $allPyFiles | Select-String -Pattern $pattern -ErrorAction SilentlyContinue

    if ($matches) {
        Write-Host "   ⚠️ Patrón XSS/Formateo HTML: $pattern" -ForegroundColor Yellow
        foreach ($match in $matches) {
            Write-Host "      $($match.Path):$($match.LineNumber)" -ForegroundColor DarkYellow
        }
        $xss_vulns += $matches.Count
    }
}

if ($xss_vulns -eq 0) {
    Write-Host "   ✅ Sin XSS obvio detectado" -ForegroundColor Green
}

# 6. Verificar .gitignore
Write-Host "`n6️⃣ Verificando .gitignore..." -ForegroundColor Yellow

if (Test-Path ".gitignore") {
    $gitignore_content = Get-Content ".gitignore"
    $critical_patterns = @(".env", ".env.local", ".env.*.local","*.env")
    $missing = @()

    foreach ($pattern in $critical_patterns) {
        $regexPattern = [regex]::Escape($pattern).Replace("\\\*", ".*")
        if (-not ($gitignore_content | Select-String -Pattern $regexPattern -Quiet)) {
            $missing += $pattern
        }
    }

    if ($missing.Count -gt 0) {
        Write-Host "   ⚠️ Faltan patrones críticos en .gitignore: $($missing -join ', ')" -ForegroundColor Red
    } else {
        Write-Host "   ✅ .gitignore bien configurado" -ForegroundColor Green
    }
} else {
    Write-Host "   ❌ .gitignore no encontrado en la raíz" -ForegroundColor Red
}

# 7. Verificar pickle
Write-Host "`n7️⃣ Verificando uso de pickle (Deserialización Insegura)..." -ForegroundColor Yellow

$pickle_matches = $allPyFiles | Select-String -Pattern "pickle\." -ErrorAction SilentlyContinue

if ($pickle_matches) {
    Write-Host "   ⚠️ Uso de pickle detectado (Riesgo de ejecución remota de código)" -ForegroundColor Yellow
    foreach ($match in $pickle_matches) {
        Write-Host "      $($match.Path):$($match.LineNumber)" -ForegroundColor DarkYellow
    }
} else {
    Write-Host "   ✅ Sin uso de pickle" -ForegroundColor Green
}

# 8. Verificar hashing
Write-Host "`n8️⃣ Verificando hashing de contraseñas..." -ForegroundColor Yellow

$hash_patterns = @("bcrypt", "argon2", "scrypt", "pbkdf2")
$has_hashing = $false

foreach ($pattern in $hash_patterns) {
    $matches = $allPyFiles | Select-String -Pattern $pattern -Quiet -ErrorAction SilentlyContinue
    if ($matches) {
        $has_hashing = $true
        break
    }
}

if ($has_hashing) {
    Write-Host "   ✅ Hashing seguro detectado en el proyecto" -ForegroundColor Green
} else {
    Write-Host "   ⚠️ No se detectó ninguna librería de hashing seguro estándar" -ForegroundColor Yellow
}

# 9. DEBUG=True
Write-Host "`n9️⃣ Verificando DEBUG mode activo..." -ForegroundColor Yellow

$debug_matches = $allPyFiles | Select-String -Pattern "DEBUG\s*=\s*True" -ErrorAction SilentlyContinue

if ($debug_matches) {
    Write-Host "   ⚠️ DEBUG=True encontrado en entorno potencial de producción" -ForegroundColor Yellow
    foreach ($match in $debug_matches) {
        Write-Host "      $($match.Path):$($match.LineNumber)" -ForegroundColor DarkYellow
    }
} else {
    Write-Host "   ✅ DEBUG activo no detectado de forma explícita" -ForegroundColor Green
}

# 10. SSL/TLS
Write-Host "`n🔟 Verificando deshabilitación de SSL/TLS..." -ForegroundColor Yellow

$ssl_patterns = @(
    "verify\s*=\s*False",
    "ssl_verify\s*=\s*False"
)

$ssl_issues = 0

foreach ($pattern in $ssl_patterns) {
    $matches = $allPyFiles | Select-String -Pattern $pattern -ErrorAction SilentlyContinue

    if ($matches) {
        Write-Host "   ❌ SSL verification deshabilitada: $pattern" -ForegroundColor Red
        foreach ($match in $matches) {
            Write-Host "      $($match.Path):$($match.LineNumber)" -ForegroundColor DarkYellow
        }
        $ssl_issues += $matches.Count
    }
}

if ($ssl_issues -eq 0) {
    Write-Host "   ✅ No se detectó bypass de validación SSL/TLS" -ForegroundColor Green
}

Write-Host "`n=====================================" -ForegroundColor Cyan
Write-Host "✅ ESCANEO DE SEGURIDAD COMPLETADO" -ForegroundColor Cyan
Write-Host "=====================================" -ForegroundColor Cyan