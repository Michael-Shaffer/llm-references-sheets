import logging
import sys

# We need to import the registry functions
try:
    from .registry import get_processor_class, list_processors
except ImportError:
    from registry import get_processor_class, list_processors

# CRITICAL: We must import the processors package to trigger the 
# auto-discovery and registration of processor classes.
try:
    import processors 
except ImportError:
    # Handle case where it might be a relative import issue
    try:
        from . import processors
    except ImportError:
        pass # If this fails, the registry might be empty, which gets caught at runtime.

logger = logging.getLogger(__name__)

class ProcessorFactory:
    """
    Factory class to instantiate processors.
    Now fully decoupled: it doesn't know about specific classes, only the registry.
    """
    
    @staticmethod
    def get_processor(document_type: str):
        processor_class = get_processor_class(document_type)
        if processor_class:
            return processor_class()
        else:
            logger.error(f"Unsupported mode: {document_type}")
            # In a real app, raise an exception instead of sys.exit so the caller can handle it
            raise ValueError(f"No processor registered for type: {document_type}. Available: {list_processors()}")

    @staticmethod
    def available_processors() -> list[str]:
        return list_processors()
