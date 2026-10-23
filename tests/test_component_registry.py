"""Unit tests for ComponentRegistry and layout micro-handlers."""

import unittest
from xml.etree import ElementTree as ET
from literature_parser.services.parsers.layout.component_registry import (
    CalloutComponentHandler,
    ComponentRegistry,
    ComponentResult,
    MarginGlossaryHandler,
    TableComponentHandler,
)


class TestComponentRegistry(unittest.TestCase):
    """Verifies that the ComponentRegistry correctly registers and dispatches micro-handlers."""

    def test_component_registry_registration(self):
        """Verifies handlers can be initialized and registered."""
        registry = ComponentRegistry()
        self.assertGreaterEqual(len(registry.handlers), 3)

        class DummyHandler:
            def can_handle(self, page_elem, fonts, context):
                return True

            def extract(self, page_elem, fonts, context):
                return [ComponentResult(
                    element_type="custom",
                    identifier="custom_1",
                    content="custom content",
                    page_num=1,
                )]

        registry.register_handler(DummyHandler())
        root = ET.Element("page")
        results, consumed = registry.dispatch_page_components(root, {}, {"page_num": 1})
        self.assertTrue(any(r.element_type == "custom" for r in results))

    def test_callout_handler_detection(self):
        """Verifies callout handler responds when callout keywords exist."""
        handler = CalloutComponentHandler()
        root = ET.Element("page")
        t = ET.SubElement(root, "text")
        t.text = "Tip: Keep in mind the following rule."
        self.assertTrue(handler.can_handle(root, {}, {}))

        t.text = "Regular paragraph text without special keywords."
        self.assertFalse(handler.can_handle(root, {}, {}))


if __name__ == "__main__":
    unittest.main()
