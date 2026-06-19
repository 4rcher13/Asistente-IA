# Script para ejecutar tests con opciones
param(
    [ValidateSet("all", "unit", "integration", "security", "coverage")]
    [string]$Type = "all"
)

Write-Host "🧪 Ejecutando tests: $Type" -ForegroundColor Cyan

switch ($Type) {
    "all" {
        python -m pytest tests/ -v --tb=short
    }
    "unit" {
        pytest tests/unit/ -v -m "unit"
    }
    "integration" {
        pytest tests/integration/ -v -m "integration"
    }
    "security" {
        pytest tests/ -v -m "security"
    }
    "coverage" {
        pytest tests/ --cov=src --cov-report=html --cov-report=term-missing
        Write-Host "
📊 Abirir: htmlcov/index.html" -ForegroundColor Green
    }
}
