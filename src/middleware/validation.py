# src/middleware/validation.py
from pydantic import ValidationError, BaseModel
from typing import Type, Any
from functools import wraps
import logging

logger = logging.getLogger(__name__)

def validate_input(schema_class: Type[BaseModel]):
    """Decorador para validar entrada automáticamente"""
    def decorator(func):
        @wraps(func)
        def wrapper(*args, **kwargs):
            try:
                # Validar primeros N argumentos contra el esquema
                validated_data = schema_class(**kwargs)
                # Reemplazar kwargs con datos validados
                return func(*args, **validated_data.dict())
            except ValidationError as e:
                logger.error(f"Validation error in {func.__name__}: {e}")
                raise ValueError(f"Invalid input: {e.errors()}")
        return wrapper
    return decorator