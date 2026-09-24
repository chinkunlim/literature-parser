"""
Verification Module: Multi-Metric Rules, Automated Suite & Local Ollama AI
==========================================================================
"""

from doc_processor.verification.rules import is_valid_dictionary_word, check_noise_strings, check_heading_ratio
from doc_processor.verification.verifier import AccuracyVerifier
from doc_processor.verification.ollama_verifier import OllamaVerifier

__all__ = [
    "is_valid_dictionary_word",
    "check_noise_strings",
    "check_heading_ratio",
    "AccuracyVerifier",
    "OllamaVerifier"
]
