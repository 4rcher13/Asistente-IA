from abc import ABC, abstractmethod

class BasePlugin(ABC):
    """
    Interfaz base para todos los plugins del asistente Icaro.
    Todo futuro plugin (Weather, System, Spotify, etc.) heredará de aquí.
    """
    
    @abstractmethod
    def can_handle(self, command: str) -> bool:
        """
        Determina si este plugin debería manejar el comando actual.
        Debe retornar True si el comando le corresponde.
        """
        pass
        
    @abstractmethod
    def execute(self, command: str):
        """
        Contiene toda la lógica de ejecución principal.
        Retorna la respuesta o resultado de la acción en forma de string.
        """
        pass
