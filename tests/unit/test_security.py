"""
Tests de seguridad
Valida protecciones contra ataques comunes
"""

import pytest
from src.schemas.input_validation import QueryInput, CommandInput, APIRequest


class TestSecurityValidation:
    """Tests de seguridad para validación de entrada"""
    
    @pytest.mark.security
    @pytest.mark.unit
    def test_sql_injection_prevention(self):
        """Debe prevenir SQL injection en queries"""
        dangerous_queries = [
            "test'; DROP TABLE users; --",
            "admin' OR '1'='1",
            "test' UNION SELECT * FROM users",
            "test'; DELETE FROM users; --",
            "test' INSERT INTO users VALUES",
        ]
        
        for query in dangerous_queries:
            with pytest.raises(ValueError):
                QueryInput(query=query)
    
    @pytest.mark.security
    @pytest.mark.unit
    def test_xss_prevention(self):
        """Debe prevenir XSS attacks"""
        xss_attempts = [
            "<script>alert('xss')</script>",
            "<img src=x onerror='alert(1)'>",
            "javascript:alert('xss')",
            "<iframe src='evil.com'>",
        ]
        
        for attempt in xss_attempts:
            with pytest.raises(ValueError):
                QueryInput(query=attempt)
    
    @pytest.mark.security
    @pytest.mark.unit
    def test_command_injection_prevention(self):
        """Debe prevenir command injection"""
        dangerous_commands = [
            "rm -rf /",
            "del C:\\",
            "ls | malicious_command",
            "cat file; shutdown",
            "dd if=/dev/zero of=/dev/sda",
        ]
        
        for cmd in dangerous_commands:
            with pytest.raises(ValueError):
                CommandInput(command=cmd)
    
    @pytest.mark.security
    @pytest.mark.unit
    def test_path_traversal_prevention(self):
        """Debe prevenir path traversal attacks"""
        dangerous_paths = [
            "/../../../etc/passwd",
            "..\\..\\windows\\system32",
            "~/.ssh/id_rsa",
            "../config/.env",
        ]
        
        for path in dangerous_paths:
            with pytest.raises(ValueError):
                APIRequest(endpoint=path)
    
    @pytest.mark.security
    @pytest.mark.unit
    def test_input_sanitization(self):
        """Debe sanitizar entrada de usuario"""
        # Query debe ser trimmed
        query = QueryInput(query="  test search  ")
        assert query.query == "test search"
        
        # Command debe ser trimmed
        cmd = CommandInput(command="  ls  ")
        assert cmd.command == "ls"
