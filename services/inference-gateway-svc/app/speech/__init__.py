"""
Speech module initialization.
"""

from .base import SpeechProvider, SpeechResult, SpeechError, SpeechMatrix, SpeechConfig
from .config import SpeechConfigManager, initialize_speech_matrix
from .providers.azure import AzureSpeechProvider
from .providers.google import GoogleSpeechProvider
from .providers.aws import AWSSpeechProvider

__all__ = [
    "SpeechProvider",
    "SpeechResult", 
    "SpeechError",
    "SpeechMatrix",
    "SpeechConfig",
    "SpeechConfigManager",
    "initialize_speech_matrix",
    "AzureSpeechProvider",
    "GoogleSpeechProvider",
    "AWSSpeechProvider"
]
