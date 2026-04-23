@echo off
set PYTHONPATH=.

:: Descomenta la siguiente linea si quieres forzar el modo terminal (sin micrófono)
:: set FORCE_TERMINAL=true

:: ── Lanzar widget UI en segundo plano (sin consola) ──────────────
start "" .\.venv\Scripts\pythonw.exe ui\widget.py

:: Pequeña pausa para que la UI arranque antes que el asistente
timeout /t 1 /nobreak > nul

:: ── Lanzar asistente principal ───────────────────────────────────
.\.venv\Scripts\python.exe -m src.main

pause
