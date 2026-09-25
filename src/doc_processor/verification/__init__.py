"""
Verification Module: Multi-Metric Rules, Automated Suite & Local Ollama AI
==========================================================================
"""

from doc_processor.verification.ollama_verifier import OllamaVerifier
from doc_processor.verification.rules import (
    check_heading_ratio,
    check_noise_strings,
    is_valid_dictionary_word,
)
from doc_processor.verification.verifier import AccuracyVerifier

__all__ = [
    "AccuracyVerifier",
    "OllamaVerifier",
    "check_heading_ratio",
    "check_noise_strings",
    "is_valid_dictionary_word"
]
