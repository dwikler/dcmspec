from rich.console import Console
from rich.table import Table, box
from rich.text import Text
from anytree import RenderTree, PreOrderIter
from typing import Optional
import logging

LEVEL_COLORS = [
    "rgb(255,255,255)",  # Node depth 0, Root: White
    "rgb(173,216,230)",  # Node depth 1, Table Level 0: Light Blue
    "rgb(135,206,250)",  # Node depth 2, Table Level 1: Sky Blue
    "rgb(0,191,255)",  # Node depth 3, Table Level 2: Deep Sky Blue
    "rgb(30,144,255)",  # Node depth 4, Table Level 3: Dodger Blue
    "rgb(0,0,255)",  # Node depth 5, Table Level 4: Blue
]


class SpecPrinter:
    def __init__(self, model, logger: Optional[logging.Logger] = None):
        """
        Initializes the input handler with an optional logger.

        Args:
            model: An instance of DICOMAttributeModel.
            logger (Optional[logging.Logger]): Logger instance to use. If None, a default logger is created.
        """
        if logger is not None and not isinstance(logger, logging.Logger):
            raise TypeError("logger must be an instance of logging.Logger or None")
        self.logger = logger or logging.getLogger(self.__class__.__name__)

        self.model = model
        self.console = Console(highlight=False)

    def print_tree(self, colorize: bool = False):
        """
        Prints the attribute model tree to the console.

        Traverses the tree structure and prints each node's name,
        tag (if available), along with its hierarchical representation.
        """
        # for pre, fill, node in RenderTree(self.attribute_model):
        #     node_display = f"{node.name}"
        #     if hasattr(node, "tag") and node.tag:
        #         node_display += f" {node.tag}"
        #     print(f"{pre}{node_display}")

        # TODO: make it independent of specific node attribute
        for pre, fill, node in RenderTree(self.model.attribute_model):
            style = LEVEL_COLORS[node.depth % len(LEVEL_COLORS)] if colorize else "default"
            pre_text = Text(pre)
            node_text = Text(f"{node.name} {getattr(node, 'elem_tag', '')}", style=style)
            self.console.print(pre_text + node_text)

    def print_table(self, colorize: bool = False):
        """Prints the attribute model tree as a flat table using rich."""
        table = Table(show_header=True, header_style="bold magenta", show_lines=True, box=box.ASCII_DOUBLE_HEAD)

        # Define the columns using the extracted headers
        for header in self.model.metadata.header:
            table.add_column(header, width=20)

        # Traverse the tree and add rows to the table
        for node in PreOrderIter(self.model.content):
            # skip the root node
            if node.name == "content":
                continue
            row = [getattr(node, attr, "") for attr in self.model.metadata.column_to_attr.values()]
            row_style = None
            if colorize:
                row_style = (
                    "yellow"
                    if self.model._is_include(node)
                    else "magenta"
                    if self.model._is_module_title(node)
                    else LEVEL_COLORS[(node.depth - 1) % len(LEVEL_COLORS)]
                )
            table.add_row(*row, style=row_style)

        self.console.print(table)
