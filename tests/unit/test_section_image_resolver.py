"""Tests for the SectionImageResolver class in dcmspec.section_image_resolver."""
from anytree import Node
from dcmspec.section_image_resolver import SectionImageResolver
from dcmspec.spec_model import SpecModel


class FakeDocHandler:
    """A stub DocHandler that records calls instead of making real network requests."""

    def __init__(self, should_fail_for=None):
        """Initialize the stub with an empty call log and an optional set of urls to fail for."""
        self.calls = []
        self.should_fail_for = should_fail_for or set()

    def download_if_needed(self, url, file_path, force=False, binary=False):
        """Record the call and simulate success/failure without real I/O."""
        self.calls.append((url, file_path, force, binary))
        if url in self.should_fail_for:
            raise RuntimeError(f"simulated failure for {url}")
        return file_path


def make_section_model(image_srcs):
    """Build a minimal SpecModel with the given metadata.image_srcs."""
    metadata = Node("metadata")
    metadata.image_srcs = image_srcs
    content = Node("content")
    return SpecModel(metadata=metadata, content=content)


def test_resolve_downloads_each_image_and_records_paths():
    """Test that resolve calls download_if_needed for each image and records relative paths."""
    doc_handler = FakeDocHandler()
    resolver = SectionImageResolver(doc_handler=doc_handler, cache_dir="/cache")
    section_model = make_section_model(["figures/PS3.3_C.1-1.svg", "figures/PS3.3_C.1-2.svg"])

    resolver.resolve(section_model, "https://example.org/part03.html")

    assert section_model.metadata.image_paths == [
        "figures/PS3.3_C.1-1.svg",
        "figures/PS3.3_C.1-2.svg",
    ]
    assert doc_handler.calls == [
        (
            "https://example.org/figures/PS3.3_C.1-1.svg",
            "/cache/standard/figures/PS3.3_C.1-1.svg",
            False,
            True,
        ),
        (
            "https://example.org/figures/PS3.3_C.1-2.svg",
            "/cache/standard/figures/PS3.3_C.1-2.svg",
            False,
            True,
        ),
    ]


def test_resolve_records_none_for_failed_image_and_continues(caplog):
    """Test that resolve records None and logs a warning for an image that fails to download."""
    doc_handler = FakeDocHandler(should_fail_for={"https://example.org/figures/broken.svg"})
    resolver = SectionImageResolver(doc_handler=doc_handler, cache_dir="/cache")
    section_model = make_section_model(["figures/broken.svg", "figures/ok.svg"])

    with caplog.at_level("WARNING"):
        resolver.resolve(section_model, "https://example.org/part03.html")

    assert section_model.metadata.image_paths == [None, "figures/ok.svg"]
    assert "Failed to download image 'figures/broken.svg'" in caplog.text


def test_resolve_passes_force_download_through():
    """Test that resolve's force_download reaches doc_handler.download_if_needed's force arg."""
    doc_handler = FakeDocHandler()
    resolver = SectionImageResolver(doc_handler=doc_handler, cache_dir="/cache")
    section_model = make_section_model(["figures/PS3.3_C.1-1.svg"])

    resolver.resolve(section_model, "https://example.org/part03.html", force_download=True)

    assert doc_handler.calls[0][2] is True


def test_resolve_with_no_images_sets_empty_list():
    """Test that resolve sets an empty image_paths list when the section has no images."""
    doc_handler = FakeDocHandler()
    resolver = SectionImageResolver(doc_handler=doc_handler, cache_dir="/cache")
    section_model = make_section_model([])

    resolver.resolve(section_model, "https://example.org/part03.html")

    assert section_model.metadata.image_paths == []
    assert doc_handler.calls == []
