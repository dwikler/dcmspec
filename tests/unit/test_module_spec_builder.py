"""Tests for the ModuleSpecBuilder class in dcmspec.module_spec_builder."""
from dcmspec.module_spec_builder import ModuleSpecBuilder
from dcmspec.section_registry import SectionRegistry
from dcmspec.spec_factory import SpecFactory

# Import fixtures and disable ruff checks as fixtures import triggers false positive warnings
from .fixtures_dom_module_sections import (
    module_with_sections_dom,  # noqa: F401
    module_with_circular_sections_dom,  # noqa: F401
)

COLUMN_TO_ATTR = {0: "elem_name", 1: "elem_tag", 2: "elem_type", 3: "elem_desc"}


class FakeDocHandler:
    """A stub DocHandler that records download calls instead of making real network requests."""

    def __init__(self):
        """Initialize the stub with an empty call log."""
        self.calls = []

    def download(self, url, file_path, binary=False):
        """Record the call and write a small placeholder file instead of downloading."""
        self.calls.append((url, file_path))
        import os
        os.makedirs(os.path.dirname(file_path), exist_ok=True)
        with open(file_path, "wb") as f:
            f.write(b"fake-image-bytes")
        return file_path


def make_builder(section_registry=None, doc_handler=None):
    """Create a ModuleSpecBuilder wired for the fixtures in this file."""
    module_factory = SpecFactory(column_to_attr=COLUMN_TO_ATTR, name_attr="elem_name")
    return ModuleSpecBuilder(
        module_factory=module_factory,
        section_registry=section_registry,
        ref_columns=[3],
        doc_handler=doc_handler or FakeDocHandler(),
    )


def test_build_from_dom_resolves_referenced_and_nested_sections(module_with_sections_dom):  # noqa: F811
    """Test that build_from_dom resolves a directly-referenced section and its own nested reference."""
    builder = make_builder()
    module_model, section_models = builder.build_from_dom(
        module_with_sections_dom, table_id="table_MODULE", url="https://example.org/part03.html",
        json_file_name="table_MODULE.json"
    )
    assert set(section_models.keys()) == {"sect_C.1", "sect_C.2"}
    assert section_models["sect_C.1"].metadata.title == "C.1 First Section"
    assert section_models["sect_C.2"].metadata.title == "C.2 Second Section"

    # The referencing attribute node keeps its section_refs attribute
    frame_label = next(c for c in module_model.content.children if c.elem_name == "Frame Label")
    assert frame_label.elem_desc_section_refs == ["sect_C.1"]

    # The non-referencing attribute node triggers no resolution (already covered by the exact
    # section_models set above, since only sect_C.1/sect_C.2 are present)
    other_attr = next(c for c in module_model.content.children if c.elem_name == "Other Attr")
    assert other_attr.elem_desc_section_refs == []


def test_build_from_dom_resolves_section_images(module_with_sections_dom):  # noqa: F811
    """Test that an image block in a resolved section gets downloaded and its cached path recorded."""
    doc_handler = FakeDocHandler()
    builder = make_builder(doc_handler=doc_handler)
    _, section_models = builder.build_from_dom(
        module_with_sections_dom, table_id="table_MODULE", url="https://example.org/part03.html",
        json_file_name="table_MODULE.json"
    )
    image_node = next(c for c in section_models["sect_C.1"].content.children if c.name.startswith("image_"))
    assert image_node.image_path == "figures/PS3.3_C.1-1.svg"
    assert doc_handler.calls == [
        ("https://example.org/figures/PS3.3_C.1-1.svg", image_node_file_path(builder, "PS3.3_C.1-1.svg"))
    ]


def image_node_file_path(builder, filename):
    """Return the expected cache file path for a downloaded section image."""
    import os
    return os.path.join(builder.section_factory.config.get_param("cache_dir"), "standard", "figures", filename)


def test_build_from_dom_shares_sections_via_registry(module_with_sections_dom):  # noqa: F811
    """Test that a shared SectionRegistry avoids re-downloading images on a second build."""
    doc_handler = FakeDocHandler()
    registry = SectionRegistry()
    builder = make_builder(section_registry=registry, doc_handler=doc_handler)

    builder.build_from_dom(
        module_with_sections_dom, table_id="table_MODULE", url="https://example.org/part03.html",
        json_file_name="table_MODULE.json"
    )
    assert len(doc_handler.calls) == 1
    assert "sect_C.1" in registry
    assert "sect_C.2" in registry

    # Second build reuses the registry: no additional image download
    builder.build_from_dom(
        module_with_sections_dom, table_id="table_MODULE", url="https://example.org/part03.html",
        json_file_name="table_MODULE.json"
    )
    assert len(doc_handler.calls) == 1


def test_build_from_dom_missing_section_warns_and_continues(module_with_sections_dom, caplog):  # noqa: F811
    """Test that a reference to a non-existent section id logs a warning instead of raising."""
    # Corrupt the reference to point at a section that doesn't exist in the DOM
    anchor = module_with_sections_dom.find("a", {"href": "#sect_C.1"})
    anchor["href"] = "#sect_DOES_NOT_EXIST"

    builder = make_builder()
    with caplog.at_level("WARNING"):
        _, section_models = builder.build_from_dom(
            module_with_sections_dom, table_id="table_MODULE", url="https://example.org/part03.html",
            json_file_name="table_MODULE.json"
        )
    assert section_models == {}
    assert "Could not resolve section 'sect_DOES_NOT_EXIST'" in caplog.text


def test_build_from_dom_circular_reference_does_not_recurse_infinitely(
    module_with_circular_sections_dom, caplog  # noqa: F811
):
    """Test that a cycle between two sections is detected and does not cause infinite recursion."""
    builder = make_builder()
    with caplog.at_level("WARNING"):
        _, section_models = builder.build_from_dom(
            module_with_circular_sections_dom, table_id="table_MODULE", url="https://example.org/part03.html",
            json_file_name="table_MODULE.json"
        )
    assert set(section_models.keys()) == {"sect_LOOP1", "sect_LOOP2"}
    assert "Circular section reference detected for 'sect_LOOP1'" in caplog.text


def test_no_ref_columns_resolves_no_sections(module_with_sections_dom):  # noqa: F811
    """Test that a ModuleSpecBuilder with no ref_columns configured resolves no sections at all."""
    module_factory = SpecFactory(column_to_attr=COLUMN_TO_ATTR, name_attr="elem_name")
    builder = ModuleSpecBuilder(module_factory=module_factory, doc_handler=FakeDocHandler())
    _, section_models = builder.build_from_dom(
        module_with_sections_dom, table_id="table_MODULE", url="https://example.org/part03.html",
        json_file_name="table_MODULE.json"
    )
    assert section_models == {}
