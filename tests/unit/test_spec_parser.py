"""Tests for the SpecParser class in dcmspec.spec_parser.

SpecParser is abstract, so these tests check that each concrete subclass complies with its contract.
A new parser must be added to the parametrized list to be checked.
"""
import inspect

import pytest

from dcmspec.csv_table_spec_parser import CSVTableSpecParser
from dcmspec.dom_section_spec_parser import DOMSectionSpecParser
from dcmspec.dom_table_spec_parser import DOMTableSpecParser

# Parameters common to all parsers; any other parameter of parse() is a parser-specific option.
COMMON_PARAMETERS = {
    "self",
    "dom",
    "table",
    "table_id",
    "column_to_attr",
    "name_attr",
    "include_depth",
    "progress_observer",
}


@pytest.mark.parametrize("parser_class", [CSVTableSpecParser, DOMSectionSpecParser, DOMTableSpecParser])
def test_parser_kwargs_defaults_match_parse_signature(parser_class):
    """Test parser_kwargs_defaults matches the options of parse(), with their defaults."""
    parameters = inspect.signature(parser_class.parse).parameters
    specific_defaults = {
        name: parameter.default
        for name, parameter in parameters.items()
        if name not in COMMON_PARAMETERS and parameter.kind is not inspect.Parameter.VAR_KEYWORD
    }
    assert parser_class.parser_kwargs_defaults == specific_defaults
