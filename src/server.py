from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
from typing import Optional
from src.core.editor_context import update_editor_context

app = FastAPI()

# CORS restringido a clientes locales (extensión VS Code, webviews)
_LOCAL_ORIGINS = [
    "http://127.0.0.1:8000",
    "http://localhost:8000",
    "vscode-webview://",
    "null",  # webviews embebidos sin origin
]
app.add_middleware(
    CORSMiddleware,
    allow_origins=_LOCAL_ORIGINS,
    allow_credentials=True,
    allow_methods=["GET", "POST"],
    allow_headers=["Content-Type"],
)

class Selection(BaseModel):
    startLine: int
    startCharacter: int
    endLine: int
    endCharacter: int
    text: str

class Context(BaseModel):
    fileName: str
    language: str
    code: str
    selection: Optional[Selection] = None
    timestamp: str

@app.get("/status")
def get_status():
    """Endpoint de salud para que la extensión de VS Code verifique la conexión."""
    return {"status": "ok", "app": "Icaro Core Server"}

@app.post("/context")
def receive_context(ctx: Context):
    # Guardar en memoria de forma thread-safe
    update_editor_context(ctx.dict())
    return {
        "message": "Context received",
        "file": ctx.fileName,
        "stats": {
            "language": ctx.language,
            "code_length": len(ctx.code),
            "has_selection": ctx.selection is not None and len(ctx.selection.text) > 0
        }
    }

