# Crear src/config.py
"""
Módulo de configuración centralizada para Asistente IA
Carga variables de entorno de .env y las valida
"""

import os
from pathlib import Path
from typing import Optional
from dotenv import load_dotenv

# Cargar .env
env_path = Path(__file__).parent.parent.parent / ".env"
if not env_path.exists():
    # En producción, las variables deben estar en el sistema
    print(f"Archivo .env no encontrado en {env_path}")
else:
    load_dotenv(dotenv_path=env_path)
    print(f"Cargado .env desde {env_path}")


class Config:
    """Configuración de la aplicación"""
    
    # ==== ENVIRONMENT ====
    ENVIRONMENT: str = os.getenv("ENVIRONMENT", "production")
    DEBUG: bool = os.getenv("DEBUG", "False").lower() == "true"
    LOG_LEVEL: str = os.getenv("LOG_LEVEL", "INFO")
    
    # ==== SECURITY ====
    SECRET_KEY: str = os.getenv("SECRET_KEY", "")
    if not SECRET_KEY:
        if ENVIRONMENT == "production":
            raise ValueError("SECRET_KEY must be set in production via environment variable")
        import secrets
        SECRET_KEY = f"dev-temp-{secrets.token_hex(16)}"
    
    JWT_SECRET: str = os.getenv("JWT_SECRET", SECRET_KEY)
    JWT_ALGORITHM: str = os.getenv("JWT_ALGORITHM", "HS256")
    JWT_EXPIRATION: int = int(os.getenv("JWT_EXPIRATION", "3600"))
    
    # ==== DATABASE ====
    DB_HOST: str = os.getenv("DB_HOST", "localhost")
    DB_PORT: int = int(os.getenv("DB_PORT", "5432"))
    DB_NAME: str = os.getenv("DB_NAME", "asistente_ia")
    DB_USER: str = os.getenv("DB_USER", "")
    DB_PASSWORD: str = os.getenv("DB_PASSWORD", "")
    
    @property
    def DATABASE_URL(self) -> str:
        """Construye URL de conexión segura a BD"""
        if self.DB_USER and self.DB_PASSWORD:
            return f"postgresql://{self.DB_USER}:{self.DB_PASSWORD}@{self.DB_HOST}:{self.DB_PORT}/{self.DB_NAME}"
        return f"postgresql://{self.DB_HOST}:{self.DB_PORT}/{self.DB_NAME}"
    
    # ==== API KEYS (No exponerlas por defecto) ====
    OPENAI_API_KEY: Optional[str] = os.getenv("API_KEY_OPENAI")
    EXTERNAL_API_KEY: Optional[str] = os.getenv("API_KEY_EXTERNAL")
    
    # ==== REDIS ====
    REDIS_URL: str = os.getenv("REDIS_URL", "redis://localhost:6379")
    
    # ==== EMAIL ====
    MAIL_SERVER: str = os.getenv("MAIL_SERVER", "localhost")
    MAIL_PORT: int = int(os.getenv("MAIL_PORT", "587"))
    MAIL_USERNAME: str = os.getenv("MAIL_USERNAME", "")
    MAIL_PASSWORD: str = os.getenv("MAIL_PASSWORD", "")
    
    @classmethod
    def validate(cls) -> None:
        """Valida configuración crítica"""
        errors = []
        
        if cls.ENVIRONMENT == "production":
            if not cls.SECRET_KEY or cls.SECRET_KEY.startswith("dev-"):
                errors.append("SECRET_KEY debe ser segura en producción")
            if cls.DEBUG:
                errors.append("DEBUG debe ser False en producción")
            if not cls.DB_PASSWORD:
                errors.append("DB_PASSWORD es requerido en producción")
        
        if errors:
            raise ValueError(f"Errores de configuración:\n" + "\n".join(f"  - {e}" for e in errors))
    
    @classmethod
    def to_dict(cls, exclude_secrets: bool = True) -> dict:
        """Retorna configuración como diccionario (opcionalmente sin secretos)"""
        config_dict = {
            "ENVIRONMENT": cls.ENVIRONMENT,
            "DEBUG": cls.DEBUG,
            "LOG_LEVEL": cls.LOG_LEVEL,
            "DB_HOST": cls.DB_HOST,
            "DB_PORT": cls.DB_PORT,
            "DB_NAME": cls.DB_NAME,
        }
        
        if not exclude_secrets:
            config_dict.update({
                "SECRET_KEY": "***" if cls.SECRET_KEY else None,
                "JWT_SECRET": "***" if cls.JWT_SECRET else None,
                "DB_PASSWORD": "***" if cls.DB_PASSWORD else None,
                "OPENAI_API_KEY": "***" if cls.OPENAI_API_KEY else None,
            })
        
        return config_dict


# Instancia global - usar: from src.config import config
config = Config()

if __name__ == "__main__":
    print("🔧 Configuración Cargada:")
    print("-" * 50)
    for key, value in config.to_dict().items():
        print(f"  {key}: {value}")
    print("-" * 50)
    print("Configuración válida")
