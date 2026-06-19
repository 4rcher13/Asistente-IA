"""
Factories para crear objetos de prueba
"""

from factory import Factory, Faker
from src.schemas import UserCreate, UserRole


class UserCreateFactory(Factory):
    """Factory para crear usuarios de prueba"""
    
    class Meta:
        model = UserCreate
    
    email = Faker("email")
    full_name = Faker("name")
    password = "SecureTest123!"


class UserResponseFactory(Factory):
    """Factory para crear responses de usuario"""
    
    class Meta:
        model = dict
    
    id = Faker("random_int")
    email = Faker("email")
    full_name = Faker("name")
    role = UserRole.USER
    created_at = Faker("date_time")
