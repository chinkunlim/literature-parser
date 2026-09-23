"""
Fingerprinting Subpackage
=========================
Document classification and publisher detection for autonomous pipeline routing.
"""

from book_processor.fingerprinting.publisher_detector import PublisherDetector
from book_processor.fingerprinting.document_classifier import DocumentClassifier

__all__ = ["PublisherDetector", "DocumentClassifier"]
