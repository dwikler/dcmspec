"""Tests for the CSVTableSpecParser class in dcmspec.csv_table_spec_parser."""
from dcmspec.csv_table_spec_parser import CSVTableSpecParser

def test_parse_happy_path():
    """Test parse returns correct metadata and content for a simple table."""
    # Arrange
    parser = CSVTableSpecParser()
    table = {
        "header": ["Name", "Tag", "Type"],
        "data": [
            ["Parent", "(0011,1001)", "1"],
            [">Child", "(0011,1002)", "2"],
        ]
    }
    column_to_attr = {0: "elem_name", 1: "elem_tag", 2: "elem_type"}

    # Act
    metadata, content = parser.parse(table, column_to_attr, name_attr="elem_name", table_id="T-1", include_depth=2)

    # Assert
    assert metadata.header == ["Name", "Tag", "Type"]
    assert metadata.column_to_attr == column_to_attr
    assert metadata.table_id == "T-1"
    assert metadata.include_depth == 2
    # Check tree structure
    names = [node.name for node in content.children]
    assert names == ["Parent"]
    child_names = [node.name for node in content.children[0].children]
    assert child_names == [">Child"]

def test_parse_table_handles_newlines_in_name():
    """Test parse_table cleans up newlines in the name column."""
    # Arrange
    parser = CSVTableSpecParser()
    tables = [
        [
            ["Parent\n", "(0011,1001)", "1"],
            [">Child\n", "(0011,1002)", "2"],
        ]
    ]
    column_to_attr = {0: "elem_name", 1: "elem_tag", 2: "elem_type"}

    # Act
    root = parser.parse_table(tables, column_to_attr, name_attr="elem_name")

    # Assert
    names = [node.name for node in root.children]
    assert names == ["Parent "]
    child_names = [node.name for node in root.children[0].children]
    assert child_names == [">Child "]

def test_parse_empty_table():
    """Test parse returns empty content for empty data."""
    # Arrange
    parser = CSVTableSpecParser()
    table = {
        "header": ["Name", "Tag", "Type"],
        "data": []
    }
    column_to_attr = {0: "elem_name", 1: "elem_tag", 2: "elem_type"}

    # Act
    metadata, content = parser.parse(table, column_to_attr, name_attr="elem_name")

    # Assert
    assert metadata.header == ["Name", "Tag", "Type"]
    assert len(content.children) == 0

def test_parse_table_handles_missing_columns():
    """Test parse_table fills missing columns with empty string."""
    # Arrange
    parser = CSVTableSpecParser()
    tables = [
        [
            ["Parent", "(0011,1001)"],  # Missing type
            [">Child"],  # Only name
        ]
    ]
    column_to_attr = {0: "elem_name", 1: "elem_tag", 2: "elem_type"}

    # Act
    root = parser.parse_table(tables, column_to_attr, name_attr="elem_name")

    # Assert
    node = root.children[0]
    child = node.children[0]
    assert hasattr(node, "elem_name")
    assert hasattr(node, "elem_tag")
    assert hasattr(node, "elem_type")
    assert node.elem_type == ""
    assert hasattr(child, "elem_name")
    assert hasattr(child, "elem_tag")
    assert hasattr(child, "elem_type")
    assert child.elem_tag == ""
    assert child.elem_type == ""

def test_parse_table_nesting():
    """Test parse_table builds correct parent-child relationships based on '>' nesting."""
    # Arrange
    parser = CSVTableSpecParser()
    tables = [
        [
            ["Parent", "(0011,1001)", "1"],
            [">Child1", "(0011,1002)", "2"],
            [">Child2", "(0011,1003)", "2"],
            [">>Grandchild", "(0011,1004)", "3"],
        ]
    ]
    column_to_attr = {0: "elem_name", 1: "elem_tag", 2: "elem_type"}

    # Act
    root = parser.parse_table(tables, column_to_attr, name_attr="elem_name")

    # Assert
    parent = root.children[0]
    assert parent.name == "Parent"
    child1 = parent.children[0]
    child2 = parent.children[1]
    assert child1.name == ">Child1"
    assert child2.name == ">Child2"
    grandchild = child2.children[0]
    assert grandchild.name == ">>Grandchild"
