"""End-to-end canary tests against the real, current DICOM standard.

Unlike tests/unit and tests/integration, these tests perform real network requests against
dicom.nema.org and assert only on structural shape (non-empty, expected columns/attributes
present) rather than pinned values, since standard content changes between releases and that
isn't what this suite protects against. It's a canary for NEMA changing table markup between
releases, one representative table per distinct pipeline path. Not run by default; see
CONTRIBUTING.md for how to run it.
"""

from dcmspec.config import Config
from dcmspec.iod_spec_builder import IODSpecBuilder
from dcmspec.iod_spec_printer import IODSpecPrinter
from dcmspec.service_attribute_defaults import UPS_COLUMNS_MAPPING, UPS_DIMSE_MAPPING, UPS_NAME_ATTR
from dcmspec.service_attribute_model import ServiceAttributeModel
from dcmspec.spec_factory import SpecFactory
from dcmspec.spec_merger import SpecMerger
from dcmspec.spec_printer import SpecPrinter
from dcmspec.ups_xhtml_doc_handler import UPSXHTMLDocHandler

PART3_URL = "https://dicom.nema.org/medical/dicom/current/output/html/part03.html"
PART6_URL = "https://dicom.nema.org/medical/dicom/current/output/chtml/part06/chapter_6.html"
PART4_UPS_URL = "https://dicom.nema.org/medical/dicom/current/output/chtml/part04/sect_CC.2.5.html"


def test_e2e_iod_composite_attributes_via_iod_spec_builder(e2e_output_dir):
    """Part 3 Composite IOD + referenced modules, via IODSpecBuilder.build_from_url."""
    config = Config(app_name="dcmspec")
    iod_factory = SpecFactory(
        column_to_attr={0: "ie", 1: "module", 2: "ref", 3: "usage"},
        name_attr="module",
        config=config,
    )
    module_factory = SpecFactory(
        column_to_attr={0: "elem_name", 1: "elem_tag", 2: "elem_type", 3: "elem_description"},
        name_attr="elem_name",
        config=config,
    )
    builder = IODSpecBuilder(iod_factory=iod_factory, module_factory=module_factory)

    model, _ = builder.build_from_url(
        url=PART3_URL,
        cache_file_name="Part3.xhtml",
        json_file_name="e2e_Part3_table_A.3-1_expanded.json",
        table_id="table_A.3-1",
        force_download=False,
    )

    assert model.content.children, "IOD model has no top-level module nodes"

    missing_module_attr = [n.name for n in model.content.children if not hasattr(n, "module")]
    assert not missing_module_attr, f"module nodes missing 'module' attribute: {missing_module_attr}"

    empty_module_nodes = [n.name for n in model.content.children if not n.children]
    assert not empty_module_nodes, f"module nodes with no attribute children: {empty_module_nodes}"

    incomplete_attr_nodes = [
        (iod_node.name, attr_node.name)
        for iod_node in model.content.children
        for attr_node in iod_node.children
        if not (hasattr(attr_node, "elem_name") and hasattr(attr_node, "elem_tag") and hasattr(attr_node, "elem_type"))
    ]
    assert not incomplete_attr_nodes, f"attribute nodes missing elem_name/elem_tag/elem_type: {incomplete_attr_nodes}"

    output_path = e2e_output_dir / "iod_composite.txt"
    IODSpecPrinter(model, output=str(output_path)).print_tree(
        attr_names=["elem_tag", "elem_type", "elem_name"], attr_widths=[11, 2, 64]
    )
    print(f"\nIOD tree written to: {output_path}")


def test_e2e_data_elements_dictionary_via_spec_factory(e2e_output_dir):
    """Part 6 Data Elements dictionary, via plain SpecFactory.create_model."""
    config = Config(app_name="dcmspec")
    factory = SpecFactory(
        column_to_attr={
            0: "elem_tag",
            1: "elem_name",
            2: "elem_keyword",
            3: "elem_vr",
            4: "elem_vm",
            5: "elem_status",
        },
        config=config,
    )
    model = factory.create_model(
        url=PART6_URL,
        cache_file_name="DataElements.xhtml",
        table_id="table_6-1",
        force_download=False,
        json_file_name="e2e_DataElements.json",
    )

    assert model.metadata.header
    assert model.content.children, "Data Elements model has no children"
    sample = model.content.children[0]
    missing_attrs = [
        a for a in ("elem_tag", "elem_name", "elem_keyword", "elem_vr", "elem_vm", "elem_status")
        if not hasattr(sample, a)
    ]
    assert not missing_attrs, f"sample data element missing attributes: {missing_attrs}"
    # Weak canary against a near-empty parse (e.g. only the header row parsing).
    assert len(model.content.children) > 1000

    output_path = e2e_output_dir / "data_elements.txt"
    SpecPrinter(model, output=str(output_path)).print_table()
    print(f"\n{len(model.content.children)} data elements written to: {output_path}")


def test_e2e_ups_dimse_attributes_via_service_attribute_model(e2e_output_dir):
    """Part 4 UPS DIMSE service attributes, via SpecFactory + UPSXHTMLDocHandler + ServiceAttributeModel."""
    config = Config(app_name="dcmspec")
    factory = SpecFactory(
        model_class=ServiceAttributeModel,
        input_handler=UPSXHTMLDocHandler(config=config),
        column_to_attr=UPS_COLUMNS_MAPPING,
        name_attr=UPS_NAME_ATTR,
        config=config,
    )
    model = factory.create_model(
        url=PART4_UPS_URL,
        cache_file_name="UPSattributes.xhtml",
        table_id="table_CC.2.5-3",
        force_download=False,
        json_file_name="e2e_UPSattributes.json",
        model_kwargs={"dimse_mapping": UPS_DIMSE_MAPPING},
    )

    assert model.content.children, "UPS attribute model has no children"
    sample = model.content.children[0]
    missing_attrs = [
        a for a in (
            "elem_name", "elem_tag", "dimse_ncreate", "dimse_nset", "dimse_final", "dimse_nget",
            "key_matching", "key_return",
        )
        if not hasattr(sample, a)
    ]
    assert not missing_attrs, f"sample UPS attribute missing attributes: {missing_attrs}"

    # Exercise the ServiceAttributeModel-specific filtering, which relies on UPSXHTMLDocHandler's
    # table patching having produced parseable requirement-type cells.
    model.select_dimse("N-CREATE")
    assert model.content.children

    output_path = e2e_output_dir / "ups_dimse.txt"
    SpecPrinter(model, output=str(output_path)).print_tree(attr_names=["elem_tag", "elem_name"], attr_widths=[11, 64])
    print(f"\nUPS DIMSE tree written to: {output_path}")


def test_e2e_module_part6_merge_via_spec_merger(e2e_output_dir):
    """Part 3 module (Patient Module) merged with Part 6 dictionary, via SpecMerger.merge_node."""
    config = Config(app_name="dcmspec")
    module_factory = SpecFactory(
        column_to_attr={0: "elem_name", 1: "elem_tag", 2: "elem_type", 3: "elem_description"},
        name_attr="elem_name",
        config=config,
    )
    module_model = module_factory.create_model(
        url=PART3_URL,
        cache_file_name="Part3.xhtml",
        json_file_name="e2e_Part3_table_C.7-1.json",
        table_id="table_C.7-1",
        force_download=False,
    )

    part6_factory = SpecFactory(
        column_to_attr={
            0: "elem_tag",
            1: "elem_name",
            2: "elem_keyword",
            3: "elem_vr",
            4: "elem_vm",
            5: "elem_status",
        },
        config=config,
    )
    part6_model = part6_factory.create_model(
        url=PART6_URL,
        cache_file_name="DataElements.xhtml",
        table_id="table_6-1",
        force_download=False,
        json_file_name="e2e_DataElements.json",
    )

    merger = SpecMerger(config=config)
    merged = merger.merge_node(
        module_model,
        part6_model,
        match_by="attribute",
        attribute_name="elem_tag",
        merge_attrs=["elem_vr", "elem_vm"],
        json_file_name="e2e_Part3_table_C.7-1_enriched.json",
        force_update=False,
    )

    assert merged.content.children, "merged Patient Module model has no children"
    matched_with_vr = [n for n in merged.content.children if getattr(n, "elem_vr", None)]
    assert matched_with_vr, "no Patient Module attribute was enriched with a VR from Part 6"

    output_path = e2e_output_dir / "module_part6_merge.txt"
    SpecPrinter(merged, output=str(output_path)).print_tree(
        attr_names=["elem_tag", "elem_type", "elem_vr", "elem_name"], attr_widths=[11, 2, 4, 64]
    )
    print(f"\nmerged module tree written to: {output_path}")
