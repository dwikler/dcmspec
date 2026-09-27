"""Integration tests for SpecFactory's model cache with real handler, parser and store.

A local XHTML table is placed in the document cache so no network access is needed.
"""

import os

import pytest

from dcmspec.config import Config
from dcmspec.spec_factory import SpecFactory

TABLE_ID = "table_X-1"
CACHE_FILE_NAME = "Part3.xhtml"
JSON_FILE_NAME = "Part3_table_X-1.json"

XHTML = """<?xml version="1.0" encoding="UTF-8"?>
<html xmlns="http://www.w3.org/1999/xhtml">
<body>
<div class="section">
<div class="table">
<a id="table_X-1"/>
<table>
<thead>
<tr><th>Attribute Name</th><th>Tag</th><th>Type</th><th>Attribute Description</th></tr>
</thead>
<tbody>
<tr><td>Patient Name</td><td>(0010,0010)</td><td>1</td><td>Name of the patient.</td></tr>
<tr><td>Patient ID</td><td>(0010,0020)</td><td>2</td><td>Identifier of the patient.</td></tr>
<tr><td>Study Date</td><td>(0008,0020)</td><td>Date of the study.</td></tr>
<tr><td colspan="4">Include <a class="xref" href="#table_X-2">Table X-2 Included Attributes</a></td></tr>
</tbody>
</table>
</div>
</div>
<div class="section">
<div class="table">
<a id="table_X-2"/>
<table>
<thead>
<tr><th>Attribute Name</th><th>Tag</th><th>Type</th><th>Attribute Description</th></tr>
</thead>
<tbody>
<tr><td>Modality</td><td>(0008,0060)</td><td>1</td><td>Type of the equipment.</td></tr>
</tbody>
</table>
</div>
</div>
</body>
</html>
"""


@pytest.fixture
def factory_builder(tmp_path, monkeypatch):
    """Return a function building SpecFactory instances that share one cache dir holding the XHTML table."""
    monkeypatch.setattr("dcmspec.config.user_cache_dir", lambda app_name: str(tmp_path / "cache"))
    monkeypatch.setattr("dcmspec.config.user_config_dir", lambda app_name: str(tmp_path / "config"))
    config = Config(app_name="dcmspec")
    standard_dir = os.path.join(config.get_param("cache_dir"), "standard")
    os.makedirs(standard_dir)
    with open(os.path.join(standard_dir, CACHE_FILE_NAME), "w", encoding="utf-8") as f:
        f.write(XHTML)

    def build(**kwargs):
        factory = SpecFactory(config=config, **kwargs)
        factory.parse_calls = 0
        real_parse = factory.table_parser.parse

        def counting_parse(*args, **parse_kwargs):
            factory.parse_calls += 1
            return real_parse(*args, **parse_kwargs)

        factory.table_parser.parse = counting_parse
        return factory

    return build


def create_model(factory, **kwargs):
    """Create the model of the test table through the given factory."""
    return factory.create_model(
        url="http://example.com/Part3.xhtml",
        cache_file_name=CACHE_FILE_NAME,
        table_id=TABLE_ID,
        json_file_name=JSON_FILE_NAME,
        **kwargs,
    )


def test_second_call_with_same_options_uses_cache(factory_builder):
    """Test a second factory with the same options loads the cached model instead of parsing."""
    first = factory_builder()
    model = create_model(first)
    second = factory_builder()
    cached_model = create_model(second)

    assert first.parse_calls == 1
    assert second.parse_calls == 0
    assert [node.name for node in cached_model.content.children] == [node.name for node in model.content.children]
    assert cached_model.metadata.header == model.metadata.header


@pytest.mark.parametrize(
    "changed_options",
    [
        {"column_to_attr": {0: "elem_name", 1: "elem_tag", 2: "elem_type", 3: "elem_desc"}},
        {"name_attr": "elem_tag"},
        {"parser_kwargs": {"unformatted": False}},
        {"parser_kwargs": {"ref_columns": [3]}},
    ],
    ids=["column_to_attr", "name_attr", "unformatted", "ref_columns"],
)
def test_changed_factory_option_reparses(factory_builder, changed_options):
    """Test a factory built with a different option reparses instead of reusing the cached model."""
    create_model(factory_builder())
    second = factory_builder(**changed_options)
    create_model(second)

    assert second.parse_calls == 1


def test_changed_include_depth_reparses(factory_builder):
    """Test a different include_depth reparses instead of reusing the cached model."""
    create_model(factory_builder(), include_depth=1)
    second = factory_builder()
    create_model(second, include_depth=2)

    assert second.parse_calls == 1


def test_changed_include_depth_is_reflected_in_model(factory_builder):
    """Test the rebuilt model includes the referenced table when include_depth grows."""
    shallow = create_model(factory_builder(), include_depth=0)
    deep = create_model(factory_builder(), include_depth=1)

    assert "modality" not in [node.name for node in shallow.content.descendants]
    assert "modality" in [node.name for node in deep.content.descendants]


def test_changed_column_to_attr_is_reflected_in_model(factory_builder):
    """Test the rebuilt model reflects the new column_to_attr, not the cached one."""
    create_model(factory_builder())
    column_to_attr = {0: "elem_name", 1: "elem_tag", 2: "elem_type", 3: "elem_desc"}
    model = create_model(factory_builder(column_to_attr=column_to_attr))

    assert all(hasattr(node, "elem_desc") for node in model.content.children)
    assert not any(hasattr(node, "elem_description") for node in model.content.children)


def test_changed_name_attr_is_reflected_in_model(factory_builder):
    """Test the rebuilt model names its nodes from the new name_attr, not the cached one."""
    default_model = create_model(factory_builder())
    model = create_model(factory_builder(name_attr="elem_tag"))

    default_names = [node.name for node in default_model.content.children]
    assert [node.name for node in model.content.children] != default_names


def test_default_parser_option_matches_cache_after_json_round_trip(factory_builder):
    """Test an option set explicitly to the parser's default matches a cache built with it omitted."""
    create_model(factory_builder())
    explicit = factory_builder(parser_kwargs={"unformatted": True})
    create_model(explicit)

    assert explicit.parse_calls == 0


def test_skipped_columns_use_cache_and_keep_realigned_column_to_attr(factory_builder):
    """Test a model built with skipped columns matches its cache and keeps int-keyed, realigned columns."""
    skip = {"parser_kwargs": {"skip_columns": [2]}}
    model = create_model(factory_builder(**skip))
    second = factory_builder(**skip)
    cached_model = create_model(second)

    realigned = {0: "elem_name", 1: "elem_tag", 2: "elem_description"}
    assert model.metadata.column_to_attr == realigned
    assert second.parse_calls == 0
    assert cached_model.metadata.column_to_attr == realigned
