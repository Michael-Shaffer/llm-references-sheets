from typing import Type, Dict
from processors.processor import Processor

_PROCESSOR_REGISTRY: Dict[str, Type[Processor]] = {}

def register_processor(name: str):
    """
    Decorator to register a processor class with a specific name.
    """
    def decorator(cls: Type[Processor]):
        _PROCESSOR_REGISTRY[name] = cls
        return cls
    return decorator

def get_processor_class(name: str) -> Type[Processor]:
    """Retrieves a processor class by name."""
    return _PROCESSOR_REGISTRY.get(name)

def list_processors() -> list[str]:
    """Lists all registered processors."""
    return list(_PROCESSOR_REGISTRY.keys())


