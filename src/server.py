from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
from typing import Optional
from src.core.editor_context import update_editor_context

app = FastAPI()

# Configurar CORS para permitir peticiones desde la extensión de VS Code u otros clientes locales
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
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

