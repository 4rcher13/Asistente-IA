"""
Tests unitarios para validación con Pydantic
"""

import pytest
from pydantic import ValidationError
from src.schemas import QueryInput, UserCreate, UserRole
from src.schemas.input_validation import CommandInput


class TestQueryInput:
    """Tests para QueryInput"""
    
    @pytest.mark.unit
    def test_valid_query(self):
        """Debe aceptar query válida"""
        query = QueryInput(query="python programming", limit=10)
        assert query.query == "python programming"
        assert query.limit == 10
        assert query.offset == 0
    
    @pytest.mark.unit
    def test_query_too_long(self):
        """Debe rechazar query > 1000 caracteres"""
        long_query = "x" * 1001
        with pytest.raises(ValidationError):
            QueryInput(query=long_query)
    
    @pytest.mark.unit
    def test_query_injection_attempt(self):
        """Debe bloquer SQL injection"""
        with pytest.raises(ValidationError):
            QueryInput(query="test; DROP TABLE users")
    
    @pytest.mark.unit
    def test_query_xss_attempt(self):
        """Debe bloquear XSS"""
        with pytest.raises(ValidationError):
            QueryInput(query="<script>alert('xss')</script>")
    
    @pytest.mark.unit
    def test_limit_validation(self):
        """Debe validar límite de resultados"""
        # Válido
        query = QueryInput(query="test", limit=100)
        assert query.limit == 100
        
        # Inválido
        with pytest.raises(ValidationError):
            QueryInput(query="test", limit=101)
        
        with pytest.raises(ValidationError):
            QueryInput(query="test", limit=0)
    
    @pytest.mark.unit
    def test_offset_validation(self):
        """Debe validar offset"""
        with pytest.raises(ValidationError):
            QueryInput(query="test", offset=-1)


class TestUserCreate:
    """Tests para creación de usuario"""
    
    @pytest.mark.unit
    def test_valid_user(self):
        """Debe crear usuario válido"""
        user = UserCreate(
            email="user@example.com",
            password="SecurePass123!",
            full_name="John Doe"
        )
        assert user.email == "user@example.com"
        assert user.full_name == "John Doe"
    
    @pytest.mark.unit
    def test_invalid_email(self):
        """Debe rechazar email inválido"""
        with pytest.raises(ValidationError):
            UserCreate(
                email="not-an-email",
                password="SecurePass123!",
                full_name="John Doe"
            )
    
    @pytest.mark.unit
    def test_weak_password_no_uppercase(self):
        """Debe rechazar contraseña sin mayúsculas"""
        with pytest.raises(ValidationError):
            UserCreate(
                email="user@example.com",
                password="securepass123!",
                full_name="John Doe"
            )
    
    @pytest.mark.unit
    def test_weak_password_no_number(self):
        """Debe rechazar contraseña sin números"""
        with pytest.raises(ValidationError):
            UserCreate(
                email="user@example.com",
                password="SecurePass!",
                full_name="John Doe"
            )
    
    @pytest.mark.unit
    def test_weak_password_no_special(self):
        """Debe rechazar contraseña sin caracteres especiales"""
        with pytest.raises(ValidationError):
            UserCreate(
                email="user@example.com",
                password="SecurePass123",
                full_name="John Doe"
            )
    
    @pytest.mark.unit
    def test_password_too_short(self):
        """Debe rechazar contraseña < 8 caracteres"""
        with pytest.raises(ValidationError):
            UserCreate(
                email="user@example.com",
                password="Pass1!",
                full_name="John Doe"
            )


class TestCommandInput:
    """Tests para validación de comandos"""
    
    @pytest.mark.unit
    def test_valid_command(self):
        """Debe aceptar comando válido"""
        cmd = CommandInput(command="ls", args=["-la"])
        assert cmd.command == "ls"
    
    @pytest.mark.unit
    def test_dangerous_command_rm(self):
        """Debe bloquear comando rm"""
        with pytest.raises(ValidationError):
            CommandInput(command="rm -rf /")
    
    @pytest.mark.unit
    def test_dangerous_command_del(self):
        """Debe bloquear comando del"""
        with pytest.raises(ValidationError):
            CommandInput(command="del C:\\")
    
    @pytest.mark.unit
    def test_pipe_injection(self):
        """Debe bloquear command injection con pipes"""
        with pytest.raises(ValidationError):
            CommandInput(command="ls | rm -rf")
