from pydantic import BaseModel
from typing import Any, ClassVar, TypeVar

T = TypeVar('T')

class CustomSecretStr:
    """A string that is displayed as '**********' in string representations."""
    
    def __init__(self, value: str):
        self._value = value
    
    def get_secret_value(self) -> str:
        """Return the secret value."""
        return self._value
    
    def __repr__(self) -> str:
        """Return '**********' instead of the actual value."""
        return f"CustomSecretStr('**********')" if self._value else "CustomSecretStr('')"
    
    def __str__(self) -> str:
        """Return '**********' instead of the actual value."""
        return "**********" if self._value else ""