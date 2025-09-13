"""IOD Explorer - GUI application for dcmspec.

This module provides a graphical user interface for exploring DICOM specifications,
allowing users to browse IODs, modules, and attributes through an interactive interface.
"""

import tkinter as tk
from tkinter import ttk, messagebox
import tkinter.font as tkfont
from tkhtmlview import HTMLLabel

from typing import List, Tuple
import re
import logging
import os

from anytree import PreOrderIter
from bs4 import BeautifulSoup

from dcmspec.config import Config
from dcmspec.iod_spec_builder import IODSpecBuilder
from dcmspec.spec_factory import SpecFactory
from dcmspec.xhtml_doc_handler import XHTMLDocHandler
from dcmspec.dom_table_spec_parser import DOMTableSpecParser

# Canonical DICOM Part 3 TOC (Table of Contents) URL
PART3_TOC_URL = "https://dicom.nema.org/medical/dicom/current/output/chtml/part03/ps3.3.html"
# Canonical DICOM Part 3 HTML URL
PART3_HTML_URL = "https://dicom.nema.org/medical/dicom/current/output/html/part03.html"


class StatusManager:
    """Handles status bar messaging with consistent logic."""
    
    def __init__(self, status_var):
        """Initialize the StatusManager.

        Args:
            status_var: A tkinter StringVar or similar object used to update the status bar text.

        """
        self.status_var = status_var
    
    def show_count_status(self, count: int):
        """Show count-based status when no selection."""
        message = f"Showing {count} IODs"
        self.status_var.set(message)
    
    def show_selection_status(self, title: str, iod_type: str, is_iod: bool = True):
        """Show selection-based status when item selected."""
        if is_iod:
            self.status_var.set(f"{title} {iod_type} • Click ▶ to expand")
        else:
            self.status_var.set(f"{iod_type}: {title}")

    def show_loading_status(self, message: str):
        """Show loading status."""
        self.status_var.set(message)


def load_app_config() -> Config:
    """Load app-specific configuration with priority search order.
    
    Search order:
    1. App-specific config files (iod_explorer_config.json) - Tier 1
        - Current directory
        - ~/.config/dcmspec/
        - App config directory (src/dcmspec/apps/iod_explorer/config/)
        - Same directory as script (legacy support)
    2. Base library config file (config.json) - Tier 2 fallback
        - Platform-specific user config directory via Config class
    3. Default values if no config files found
    
    Note: The base Config class always looks for a config file. When we pass
    config_file=None, it uses user_config_dir(app_name)/config.json as default.
    
    Returns:
        Config: Configuration object with app-specific settings.
        
    """
    import os

    # Look for app-specific config file in several locations (highest priority)
    app_config_locations = [
        "iod_explorer_config.json",  # Current directory
        os.path.expanduser("~/.config/dcmspec/iod_explorer_config.json"),  # User config
        os.path.join(os.path.dirname(__file__), "config", "iod_explorer_config.json"),  # App config dir
        os.path.join(os.path.dirname(__file__), "iod_explorer_config.json"),  # Same dir as script (legacy)
    ]

    config_file = next(
        (
            location
            for location in app_config_locations
            if os.path.exists(location)
        ),
        None,
    )
    # If no app-specific config found, let Config class use its default location
    # This will be: user_config_dir("iod_explorer")/config.json
    config = Config(app_name="iod_explorer", config_file=config_file)

    # Set default log level if not specified
    if config.get_param("log_level") is None:
        config.set_param("log_level", "INFO")

    return config


def setup_logger(config: Config) -> logging.Logger:
    """Set up logger with configurable level from config.
    
    Args:
        config (Config): Configuration object containing log_level setting.
        
    Returns:
        logging.Logger: Configured logger instance.
        
    """
    logger = logging.getLogger("iod_explorer")
    
    # Remove any existing handlers to avoid duplicates
    for handler in logger.handlers[:]:
        logger.removeHandler(handler)
    
    # Create console handler
    console_handler = logging.StreamHandler()
    
    # Get log level from config
    log_level_str = config.get_param("log_level") or "INFO"
    log_level = getattr(logging, log_level_str.upper(), logging.INFO)
    
    logger.setLevel(log_level)
    console_handler.setLevel(log_level)
    
    # Create formatter
    formatter = logging.Formatter('%(asctime)s - %(name)s - %(levelname)s - %(message)s')
    console_handler.setFormatter(formatter)
    
    # Add handler to logger
    logger.addHandler(console_handler)
    
    return logger


class IODExplorer:
    """Main window for the IOD Explorer application."""

    def __init__(self, root: tk.Tk):
        """Initialize the IOD Explorer application.

        This method initializes the backend services and domain model, as well as the frontend controllers and views.
        """
        # --- Backend Services ---

        # Load app-specific configuration
        self.config = load_app_config()
        # Initialize logger using configuration
        self.logger = setup_logger(self.config)

        # Log startup information
        self.logger.info("Starting IOD Explorer")
        # Log configuration information at INFO level
        log_level_configured = self.config.get_param('log_level') or 'INFO'
        config_source = ("app-specific" if self.config.config_file and 
                        "iod_explorer_config.json" in self.config.config_file else "default")
        self.logger.info(f"Logging configured: level={log_level_configured.upper()}, source={config_source}")
        # Log operational configuration at INFO level (important for users to know)
        config_file_display = self.config.config_file or "none (using defaults)"
        self.logger.info(f"Config file: {config_file_display}")
        self.logger.info(f"Cache directory: {self.config.cache_dir}")

        # --- Domain Model ---

        # Initialize document handler for DICOM standard XHTML documents
        self.doc_handler = XHTMLDocHandler(config=self.config, logger=self.logger)
        # Initialize DOM parser for DICOM standard version extraction
        self.dom_parser = DOMTableSpecParser(logger=self.logger)
        # URL for DICOM Part 3 Table of Contents
        self.part3_toc_url = PART3_TOC_URL
        # Initialize list of all IODs
        self.iod_list = []
        # Store IOD models to keep AnyTree nodes in memory
        self.iod_models = {}  # table_id -> model mapping
        # Store DICOM version
        self.dicom_version = "Unknown"

        # --- Frontend State / Controller ---

        # --- View ---

        self.root = root
        self.root.title("IOD Explorer")
        self._init_window_geometry()
        self.setup_ui()

        # Load and display IOD modules in the UI (not initialization, but triggers initial data load and view update)
        self.load_iod_modules()

    def _init_window_geometry(self):
        """Set window size and center it on screen."""
        window_width = 1200
        window_height = 700
        screen_width = self.root.winfo_screenwidth()
        screen_height = self.root.winfo_screenheight()
        x = (screen_width - window_width) // 2
        y = (screen_height - window_height) // 2
        self.root.geometry(f"{window_width}x{window_height}+{x}+{y}")
    
    def setup_ui(self):
        """Set up the user interface."""
        # Create main frame
        main_frame = ttk.Frame(self.root)
        main_frame.pack(fill=tk.BOTH, expand=True, padx=10, pady=10)

        # Create top frame for controls and labels
        top_frame = ttk.Frame(main_frame)
        top_frame.pack(fill=tk.X, pady=(0, 10))

        # Add version label in top frame
        self.version_label = ttk.Label(top_frame, text="", font=("Arial", 10))
        self.version_label.pack(side=tk.LEFT)
        
        # Create resizable paned window for IOD list and details
        paned_window = ttk.PanedWindow(main_frame, orient=tk.HORIZONTAL)
        paned_window.pack(fill=tk.BOTH, expand=True)
        
        # Left panel container
        left_panel = ttk.Frame(paned_window)
        paned_window.add(left_panel, weight=1)
        
        # Right panel container  
        right_panel = ttk.Frame(paned_window)
        paned_window.add(right_panel, weight=1)
        
        # Left panel header
        header_frame = ttk.Frame(left_panel)
        header_frame.pack(fill=tk.X, pady=(0, 5))
        
        iod_list_label = ttk.Label(header_frame, text="DICOM IOD List", font=("Arial", 12, "bold"))
        iod_list_label.pack(side=tk.LEFT)
        
        # Right panel header
        details_header_frame = ttk.Frame(right_panel)
        details_header_frame.pack(fill=tk.X, pady=(0, 5))
        
        details_label_header = ttk.Label(details_header_frame, text="Details", font=("Arial", 12, "bold"))
        details_label_header.pack(side=tk.LEFT)
        
        # Left frame for treeview
        left_frame = ttk.Frame(left_panel)
        left_frame.pack(fill=tk.BOTH, expand=True)
        
        # Configure grid for treeview area
        left_frame.columnconfigure(0, weight=1)  # Treeview column expands
        left_frame.columnconfigure(1, weight=0)  # Scrollbar column fixed
        left_frame.rowconfigure(0, weight=1)     # Treeview row expands
        left_frame.rowconfigure(1, weight=0)     # Scrollbar row fixed
        
        # Treeview with scrollbar - configure with monospaced font for better tag display
        self.tree = ttk.Treeview(
            left_frame, 
            columns=("iod_type", "usage"), 
            show="tree headings"
        )
        
        # Configure monospaced font using TTK style
        style = ttk.Style()
        
        # Configure monospaced font - simple preference stack
        available_fonts = tkfont.families()
        
        # Preferred monospaced fonts in order of preference
        font_preferences = ["Menlo", "Monaco", "Courier New", "Andale Mono", "TkFixedFont"]
        
        # Select the first available font from our preference list
        selected_font = "TkFixedFont"  # System default monospace fallback
        
        for font_name in font_preferences:
            if font_name in available_fonts or font_name == "TkFixedFont":
                selected_font = font_name
                break
        self.logger.debug(f"Selected monospaced font: {selected_font}")
        
        # Configure the treeview with the selected font
        style.configure("Treeview", font=(selected_font, 10))
        style.configure("Treeview.Heading", font=("Arial", 10, "bold"))
        
        # Add left padding to treeview items for better alignment
        style.configure("Treeview", padding=(5, 0))

        # Verify the configuration
        actual_font = style.lookup("Treeview", "font")
        self.logger.debug(f"Final font configuration: {actual_font}")
        self.tree.heading("#0", text="Name")
        self.tree.heading("iod_type", text="Kind")
        self.tree.heading("usage", text="")
        self.tree.column("#0", width=400)
        self.tree.column("iod_type", width=100, stretch=tk.NO)
        self.tree.column("usage", width=30, stretch=tk.NO)  # Small column for usage icon

        # Grid layout for treeview and scrollbars
        self.tree.grid(row=0, column=0, sticky="nsew")
        
        # Scrollbars for treeview
        tree_scroll_y = ttk.Scrollbar(left_frame, orient=tk.VERTICAL, command=self.tree.yview)
        tree_scroll_x = ttk.Scrollbar(left_frame, orient=tk.HORIZONTAL, command=self.tree.xview)
        self.tree.configure(yscrollcommand=tree_scroll_y.set, xscrollcommand=tree_scroll_x.set)
        
        tree_scroll_y.grid(row=0, column=1, sticky="ns")
        tree_scroll_x.grid(row=1, column=0, sticky="ew")
        
        # Right frame for details
        right_frame = ttk.Frame(right_panel)
        right_frame.pack(fill=tk.BOTH, expand=True)
        
        # Configure grid for details area
        right_frame.columnconfigure(0, weight=1)  # Text column expands
        right_frame.columnconfigure(1, weight=0)  # Scrollbar column fixed
        right_frame.rowconfigure(0, weight=1)     # Text row expands
        right_frame.rowconfigure(1, weight=0)     # Scrollbar row fixed

        # Details text in HTML area with grid layout, using the selected font and size
        self.details_text = HTMLLabel(
            right_frame,
            html=(
                f'<div style="font-family: {selected_font}; font-size: 10px;">'
                f'<span>Select an IOD to view details.</span><br>'
                f'</div>'
            ),
            width=50,
            height=30
        )
        self.details_text.grid(row=0, column=0, sticky="nsew")
        self.details_font_family = selected_font  # Store for later use
        self.details_font_size = 10

        # Add scrollbars that match the treeview style
        details_scroll_y = ttk.Scrollbar(right_frame, orient=tk.VERTICAL, command=self.details_text.yview)
        details_scroll_x = ttk.Scrollbar(right_frame, orient=tk.HORIZONTAL, command=self.details_text.xview)
        self.details_text.configure(yscrollcommand=details_scroll_y.set, xscrollcommand=details_scroll_x.set)
        
        details_scroll_y.grid(row=0, column=1, sticky="ns")
        details_scroll_x.grid(row=1, column=0, sticky="ew")
        
        # Bind treeview selection event
        self.tree.bind("<<TreeviewSelect>>", self.on_tree_select)

        # Status bar
        status_frame = ttk.Frame(main_frame)
        status_frame.pack(fill=tk.X, side=tk.BOTTOM, pady=(5, 0))
        
        self.status_var = tk.StringVar()
        self.status_var.set("Ready")
        
        # Initialize status manager
        self.status_manager = StatusManager(self.status_var)
        
        status_bar = ttk.Label(status_frame, textvariable=self.status_var, relief=tk.FLAT)
        status_bar.pack(side=tk.LEFT, fill=tk.X, expand=True)

    def load_iod_modules(self):
        """Load IOD modules from the DICOM specification."""
        self.status_var.set("Loading IOD modules...")
        self.root.update()

        self._last_progress_percent = -1  # Add this line before defining the callback

        def progress_callback(percent):
            # Update the status bar with the current download progress
            if percent == -1:
                # Indeterminate progress
                self.status_var.set("Downloading IOD modules... (progress unknown)")
                self.root.update()
                self._last_progress_percent = percent
            elif (percent % 10 == 0 or percent == 100) and percent != self._last_progress_percent:
                # Update every 10% and only if the percent changedÒ
                self.status_var.set(f"Downloading IOD modules... {percent}%")
                self.root.update()
                self._last_progress_percent = percent

        try:
            # Clear existing items
            for item in self.tree.get_children():
                self.tree.delete(item)

            # Use XHTMLDocHandler to download and parse the HTML with caching
            cache_file_name = "ps3.3.html"
            soup = self.doc_handler.load_document(
                cache_file_name=cache_file_name,
                url=self.part3_toc_url,
                progress_callback=progress_callback
            )

            # Extract and display DICOM version using the library method
            self.dicom_version = self.dom_parser.get_version(soup, "")
            self.version_label.config(text=f"Version {self.dicom_version}")

            # Find the list of tables div
            list_of_tables = soup.find('div', class_='list-of-tables')
            if not list_of_tables:
                messagebox.showerror("Error", "Could not find list-of-tables section")
                return

            # Extract list of IODs
            iod_list = self.extract_iod_list(list_of_tables)

            # Store the data
            self.iod_list = iod_list

            # Populate the treeview directly
            self.populate_treeview(iod_list)

            # Update status
            self.status_manager.show_count_status(count=len(iod_list))

        except RuntimeError as e:
            messagebox.showerror("Error", f"Failed to load DICOM specification:\n{str(e)}")
            self.status_var.set("Error loading modules")
        except Exception as e:
            messagebox.showerror("Error", f"An error occurred:\n{str(e)}")
            self.status_var.set("Error loading modules")
    
    def extract_iod_list(self, list_of_tables) -> List[Tuple[str, str, str, str]]:
        """Extract IOD list from the list of tables section.
        
        Returns:
            List of tuples (title, table_id, href, iod_type)
            
        """
        iod_list = []
        
        # Find all dt elements
        dt_elements = list_of_tables.find_all('dt')
        
        for dt in dt_elements:
            # Find anchor tags within the dt
            anchor = dt.find('a')
            if anchor and anchor.get('href'):
                href = anchor.get('href')
                text = anchor.get_text(strip=True)
                
                # Check if this is an IOD Modules table
                if 'IOD Modules' in text:
                    # Extract table ID from href (after the #)
                    if '#' in href:
                        table_id = href.split('#')[-1]
                    else:
                        # Fallback: try to extract from href path
                        table_id = href.split('/')[-1].replace('.html', '')
                    
                    # Extract the title (remove the table number prefix)
                    title_match = re.match(r'^[A-Z]?\.\d+(?:\.\d+)*-\d+\.\s*(.+)$', text)
                    title = title_match[1] if title_match else text
                    
                    # Strip " IOD Modules" from the end of the title
                    title = title.removesuffix(" IOD Modules")
                    
                    # Determine IOD type based on table_id
                    iod_type = ("Composite" if "_A." in table_id else 
                               "Normalized" if "_B." in table_id else "Other")
                    
                    iod_list.append((title, table_id, href, iod_type))
        
        return iod_list
    
    def populate_treeview(self, iod_modules: List[Tuple[str, str, str, str]]):
        """Populate the treeview with IOD modules."""
        for title, table_id, href, iod_type in iod_modules:
            self.tree.insert("", tk.END, text=title, values=(iod_type, ""), 
                            tags=(table_id, iod_type))

    def _is_model_cached(self, table_id: str) -> bool:
        """Check if the IOD model is already cached."""
        model_file_name = f"Part3_{table_id}_expanded.json"
        cache_file_path = os.path.join(self.config.cache_dir, "model", model_file_name)
        exists = os.path.exists(cache_file_path)
        return exists

    def on_tree_select(self, event):
        """Handle treeview selection event."""
        selection = self.tree.selection()
        if not selection:
            return

        # Get selected item data
        item = selection[0]
        item_values = self.tree.item(item, "values")
        title = self.tree.item(item, "text")
        tags = self.tree.item(item, "tags")

        # Determine if this is a top-level IOD or a module/attribute item
        if self._is_top_level_iod_item(tags):
            self._handle_iod_selection(item, title, tags)
        else:
            self._handle_module_attribute_selection(item, item_values, title, tags)

    def _is_top_level_iod_item(self, tags):
        """Check if the selected item is a top-level IOD item.

        A top-level IOD item is identified by its tag starting with "table_".
        """
        return (tags and 
                isinstance(tags[0], str) and 
                tags[0].startswith("table_"))

    def _handle_iod_selection(self, item, title, tags):
        """Handle selection of a top-level IOD item."""
        table_id = tags[0]
        iod_type = tags[1] if len(tags) > 1 else "Unknown"

        # Update status
        self.status_manager.show_selection_status(title, iod_type, is_iod=True)

        # Check if IOD spec model is already loaded in memory
        if self.iod_models.get(table_id):
            self._update_details_text(table_id, title, iod_type)
            return

        # Load IOD model otherwise (from cache or from web)
        self._load_iod_model(item, table_id, title, iod_type, is_cached=self._is_model_cached(table_id))

    def _load_iod_model(self, item, table_id, title, iod_type, is_cached=True):
        """Load IOD model from cache or web.
        
        Args:
            item: The tree item to populate with the IOD structure
            table_id: The table identifier for the IOD
            title: The IOD title for display
            iod_type: The IOD type (Composite, Normalized, etc.)
            is_cached: The flag indicating if the model is cached

        """
        try:
            # Update the status bar with loading information
            if is_cached:
                self.status_manager.show_loading_status(f"Loading {title} from cache...")
            else:
                self.status_manager.show_loading_status(f"Loading {title} (this may take a moment)...")
            
            self.root.update()

            # Build the IOD model and populate the treeview
            model, _ = self._build_iod_model(table_id, self.logger)
            self._update_treeview_and_details(item, model, table_id, title, iod_type)

        except Exception as e:
            self._handle_iod_loading_error(e, table_id, title, iod_type)

    def _update_treeview_and_details(self, item, model, table_id, title, iod_type):
        """Update the treeview and the details pane with the loaded IOD model."""
        if model:
            # Store the model in memory
            self.iod_models[table_id] = model
            
            if model.content:
                # Populate the tree item with the IOD structure
                self._populate_treeview_item(item, model.content)
            
            self._update_details_text(table_id, title, iod_type)
            self.status_manager.show_selection_status(title, iod_type, is_iod=True)

    def _handle_iod_loading_error(self, error, table_id, title, iod_type):
        """Handle errors that occur during IOD model loading."""
        if "No module models were found" in str(error):
            detailed_msg = (f"Failed to load IOD structure for {title}:\n\n"
                            f"The IOD references modules that could not be found or parsed. "
                            f"This may happen if:\n"
                            f"• Module reference tables are missing from the DICOM specification\n"
                            f"• Module tables have different naming conventions\n"
                            f"• The IOD table format is not supported\n\n"
                            f"Technical details: {str(error)}")
            messagebox.showwarning("IOD Structure Not Available", detailed_msg)
            self.logger.warning(f"Failed to build IOD model for {table_id}: {str(error)}")
        else:
            messagebox.showerror("Error", f"Failed to load IOD structure:\n{str(error)}")

        self._update_details_text(table_id, title, iod_type)
        self.status_manager.show_selection_status(title, iod_type, is_iod=True)

    def _handle_module_attribute_selection(self, item, item_values, title, tags):
        """Handle selection of a module or attribute item."""
        node_type = item_values[0] if len(item_values) > 0 else "Unknown"
        usage = item_values[1] if len(item_values) > 1 else ""

        # Find the corresponding AnyTree node
        node = self._find_node_from_path(item, tags)
        display_path = self._build_readable_path(node) if node else title

        # Generate details HTML depending on node type
        details = self._generate_node_details(node_type, node, title, usage)

        # Update UI
        self._update_details_html(details)
        self.status_var.set(f"Selected: {node_type} - {display_path}")

    def _find_node_from_path(self, item, tags):
        """Find the AnyTree node corresponding to the selected tree item."""
        if not tags or len(tags) == 0:
            return None

        node_path = tags[0]
        table_id = self._find_parent_table_id(item)
        
        if not table_id or table_id not in self.iod_models:
            return None

        model = self.iod_models[table_id]
        if not model or not hasattr(model, 'content') or not model.content:
            return None

        return self._traverse_node_path(model.content, node_path)

    def _find_parent_table_id(self, item):
        """Walk up the tree to find the parent IOD's table_id."""
        current_item = item
        while current_item:
            parent_item = self.tree.parent(current_item)
            if not parent_item:  # This is a root item
                item_tags = self.tree.item(current_item, "tags")
                if item_tags and item_tags[0].startswith("table_"):
                    return item_tags[0]
                break
            current_item = parent_item
        return None

    def _traverse_node_path(self, root_node, node_path):
        """Traverse the AnyTree structure to find the node at the given path."""
        try:
            path_parts = node_path.split("/")
            current_node = root_node

            # Navigate through the path (skip the first part which is the root)
            for part in path_parts[1:]:
                found = False
                for child in current_node.children:
                    if str(child.name) == part:
                        current_node = child
                        found = True
                        break
                if not found:
                    return None
            
            return current_node
        except Exception as e:
            self.logger.debug(f"Error finding node at path {node_path}: {e}")
            return None

    def _generate_node_details(self, node_type, node, title, usage):
        """Generate HTML details for a module or attribute node."""
        if node_type == "Module" and node:
            return self._generate_module_details(node)
        elif node_type == "Attribute" and node:
            return self._generate_attribute_details(node)
        else:
            return self._generate_fallback_details(title, node_type, usage)

    def _generate_module_details(self, node):
        """Generate HTML details for a module node."""
        name = getattr(node, 'module', 'Unknown Module')
        usage = getattr(node, 'usage', '')
        module_ref = getattr(node, 'ref', '')
        ie = getattr(node, 'ie', '')

        details = f"<h2>{name} Module</h2>"

        if ie:
            details += f"<span><b>Information Entity:</b> {ie}</span><br>"

        if usage:
            usage_display = self._format_usage_display(usage)
            details += f"<span><b>Usage:</b> {usage_display}</span><br>"

        if module_ref:
            details += self._format_module_reference(module_ref)
        return details

    def _generate_attribute_details(self, node):
        """Generate HTML details for an attribute node."""
        elem_name = getattr(node, 'elem_name', 'Unknown')
        elem_tag = getattr(node, 'elem_tag', '')
        elem_type = getattr(node, 'elem_type', '')
        elem_description = getattr(node, 'elem_description', '')

        details = f"<h2>{elem_name} Attribute</h2>"

        if elem_tag:
            details += f"<span><b>Tag:</b> {elem_tag}</span><br>"
        
        if elem_type:
            type_display = self._format_type_display(elem_type)
            details += f"<span><b>Type:</b> {type_display}</span><br>"
        
        if elem_description:
            details += f"{elem_description}"

        return details

    def _generate_fallback_details(self, title, node_type, usage):
        """Generate fallback HTML details when node is not available."""
        details = f"<h2>{title} {node_type}</h2>"
        if usage:
            details += f"<span><b>Usage/Type:</b> {usage}</span><br>"
        return details

    def _format_usage_display(self, usage):
        """Format usage code into a readable display string."""
        if usage.startswith("M"):
            return "Mandatory (M)"
        elif usage.startswith("U"):
            return "User Optional (U)"
        elif usage.startswith("C"):
            if len(usage) > 1 and " - " in usage:
                conditional_part = usage[usage.find(" - ") + 3:]
                return f"Conditional (C) - {conditional_part}"
            else:
                return "Conditional (C)"
        else:
            return usage

    def _format_module_reference(self, module_ref: str) -> str:
        """Format module reference as an HTML anchor into a DICOM Part 3 URL."""
        # Use the built-in 'xml' parser for both full documents and fragments,
        # since DICOM standard files and cell values are well-formed XHTML.
        soup = BeautifulSoup(module_ref, "xml")
        anchor = soup.find("a", class_="xref")
        if not anchor or not anchor.has_attr("href"):
            return f"<span><b>Reference:</b> {module_ref}</span><br>"
        href = anchor["href"]
        module_url = f"{PART3_HTML_URL}{href}" if href.startswith("#") else href
        return (
            f'<span><b>Reference:</b> '
            f'<a href="{module_url}" target="_blank">{anchor.get_text(strip=True)}</a>'
            f'</span><br>'
        )

    def _format_type_display(self, elem_type):
        """Format DICOM attribute type into a readable display string."""
        type_map = {
            "1": "Mandatory (1)",
            "1C": "Conditional (1C)",
            "2": "Mandatory, may be empty (2)",
            "2C": "Conditional, may be empty (2C)",
            "3": "Optional (3)",
            "": "Unspecified"
        }
        return type_map.get(elem_type, f"Other ({elem_type})" if elem_type else "Unspecified")

    def _update_details_html(self, details):
        """Update the details pane with formatted HTML."""
        self.details_text.set_html(
            f'<div style="font-family: {self.details_font_family}; '
            f'font-size: {self.details_font_size}px;">{details}</div>'
        )

    
    def _build_iod_model(self, table_id: str, logger: logging.Logger):
        """Build the IOD model for the given table_id using the IODSpecBuilder API.
        
        This method uses the IODSpecBuilder.build_from_url() method which handles:
        - Cache detection and loading (fast for cached models)
        - Web download and parsing (slower for non-cached models)
        - Model building and JSON serialization
        
        The method is called both:
        1. Directly for cached models (fast, no progress dialog needed)
        2. From background threads with progress dialogs for non-cached models
        
        Args:
            table_id (str): The table identifier (e.g., "table_A.49-1")
            logger (logging.Logger): Logger instance for progress tracking and debugging
            
        Returns:
            IOD model object with content attribute containing the AnyTree structure,
            or None if building failed.

        """
        url = PART3_HTML_URL
        cache_file_name = "Part3.xhtml"
        model_file_name = f"Part3_{table_id}_expanded.json"
        
        # Determine if this is a composite or normalized IOD
        composite_iod = "_A." in table_id
        
        # Create the IOD specification factory
        c_iod_columns_mapping = {0: "ie", 1: "module", 2: "ref", 3: "usage"}
        c_iod_unformatted = {0: True, 1: True, 2: False, 3: True}
        n_iod_columns_mapping = {0: "module", 1: "ref", 2: "usage"}
        n_iod_unformatted = {0: True, 1: False, 2: True}
        iod_columns_mapping = c_iod_columns_mapping if composite_iod else n_iod_columns_mapping
        iod_unformatted = c_iod_unformatted if composite_iod else n_iod_unformatted
        iod_factory = SpecFactory(
            column_to_attr=iod_columns_mapping, 
            name_attr="module",
            config=self.config,
            logger=logger,  # Use the custom logger for progress tracking
            parser_kwargs={"unformatted": iod_unformatted}
        )
        
        # Create the Modules specification factory

        # Ensure that the Attribute Description is parsed as formatted HTML by
        # setting unformatted to False for elem_description (column 3), others remain True
        parser_kwargs = {"unformatted": {0: True, 1: True, 2: True, 3: False}}
        # Skip the elem_type column for normalized IODs (for Module tables where it does exist such as SOP Common)
        if not composite_iod:
            parser_kwargs["skip_columns"] = [2]

        module_factory = SpecFactory(
            column_to_attr={0: "elem_name", 1: "elem_tag", 2: "elem_type", 3: "elem_description"},
            name_attr="elem_name",
            parser_kwargs=parser_kwargs,
            config=self.config,
            logger=logger,  # Use the custom logger for progress tracking
        )
        
        # Create the IOD builder
        builder = IODSpecBuilder(
            iod_factory=iod_factory, 
            module_factory=module_factory,
            logger=logger,  # Use the custom logger for progress tracking
        )
        
        # Build and return the IOD specification model
        return builder.build_from_url(
            url=url,
            cache_file_name=cache_file_name,
            json_file_name=model_file_name,
            table_id=table_id,
            force_download=False,
        )
    
    def _populate_treeview_item(self, parent_item, content):
        """Populate the treeview item with IOD structure from the model content using AnyTree traversal."""
        if not content:
            return

        # Use AnyTree's PreOrderIter to traverse the entire tree structure
        # Skip the root content node itself, start with its children
        tree_items = {}  # Map from node to tree item for building hierarchy

        for node in PreOrderIter(content):
            if node == content:
                # Skip the root content node
                continue

            # Determine the parent tree item
            if node.parent == content:
                # Direct child of content - parent is the IOD item
                parent_tree_item = parent_item
            else:
                # Child of another node - find parent in our mapping
                parent_tree_item = tree_items.get(node.parent, parent_item)

            # Determine node type and display text
            if hasattr(node, 'module'):
                # This is a module node of an IOD
                module_name = getattr(node, 'module', 'Unknown Module')

                display_text = module_name
                node_type = "Module"

                # Check if this is a normalized IOD from the parent item's IOD type
                parent_values = self.tree.item(parent_item, "values") if parent_item else None
                is_normalized = parent_values and len(parent_values) > 0 and parent_values[0] == "Normalized"

                # For normalized IODs, modules don't have usage information
                # For composite IODs, keep only the first character of usage
                usage = "" if is_normalized else getattr(node, 'usage', '')[:1]

            elif hasattr(node, 'elem_name'):
                # This is an attribute node
                attr_name = getattr(node, 'elem_name', 'Unknown Attribute')
                attr_tag = getattr(node, 'elem_tag', '')
                elem_type = getattr(node, 'elem_type', '')

                display_text = f"{attr_tag} {attr_name}" if attr_tag else attr_name

                node_type = "Attribute"
                usage = elem_type  # Use elem_type for attributes in usage column

            else:
                # Unknown node type
                display_text = str(getattr(node, 'name', 'Unknown Node'))
                node_type = "Unknown"
                usage = ""

            # Insert the node into the tree, store node path in tags
            # Node path provides a unique identifier that can be used to find the node later
            node_path = "/".join([str(n.name) for n in node.path])

            tree_item = self.tree.insert(
                parent_tree_item, tk.END, text=display_text, 
                values=(node_type, usage, ""), tags=(node_path,)  # Empty string for favorite column
            )
            tree_items[node] = tree_item
    
    def _update_details_text(self, table_id: str, title: str, iod_type: str):
        """Update the details text area with IOD specification information only."""
        # Build details as HTML using <span> and <br> for spacing (tkhtmlview ignores margin styles)
        details = (
            f'<h1>{title} IOD</h1>'
        )

        # Check if we have a model for this IOD
        if table_id in self.iod_models and self.iod_models[table_id] and hasattr(self.iod_models[table_id], 'content'):
            # Add reference information using <span> and <br>
            if iod_type == "Composite":
                details += '<div style="margin-bottom: 1em;"><b>Kind: </b>Composite</div>'
            elif iod_type == "Normalized":
                details += '<div style="margin-bottom: 1em;"><b>Kind: </b>Normalized</div>'
            else:
                details += '<div style="margin-bottom: 1em;"><b>Kind: </b>Other IOD type</div>'
            details += f'<span>loaded from DICOM PS3.3 Table {table_id.replace("table_", "")}</span><br>'

        else:
            details += '<span>IOD structure not available.</span><br>'
            details += (
                '<span>'
                "This may occur if the IOD references modules that cannot be found or "
                "parsed from the DICOM specification."
                '</span><br>'
            )

        html = (
            f'<div style="font-family: {self.details_font_family}; '
            f'font-size: {self.details_font_size}px;">{details}</div>'
        )
        self.details_text.set_html(html)
        
    def _build_readable_path(self, node):
        """Build a human-readable path from the AnyTree using node names."""
        path_parts = []
        
        # Walk up the tree from the current node to the root
        current = node
        while current and current.parent:  # Stop before the root content node
            if hasattr(current, 'module'):
                # This is a module node - use module name
                node_name = getattr(current, 'module', 'Unknown Module')
            elif hasattr(current, 'elem_name'):
                # This is an attribute node - use elem_name
                elem_name = getattr(current, 'elem_name', 'Unknown Attribute')
                node_name = re.sub(r'^(?:&gt;|>)+', '', elem_name)  # Remove leading > characters
            else:
                # Fallback to node name
                node_name = str(getattr(current, 'name', 'Unknown'))
            
            path_parts.insert(0, node_name)  # Insert at beginning to build path from root
            current = current.parent
        
        # Join with " > " separator for a readable hierarchical path
        return "/".join(path_parts)

def main() -> None:
    """Entry point for the IOD Explorer GUI application.
    
    Loads configuration and starts the GUI. Configuration can be customized
    by placing a iod_explorer_config.json file in:
    1. Current directory
    2. ~/.config/dcmspec/
    3. App config directory (src/dcmspec/apps/iod_explorer/config/)
    4. Same directory as script (legacy support)
    
    Example config file:
    {
        "cache_dir": "./cache",
        "log_level": "INFO"
    }
    
    Supported log levels:
    - DEBUG: Detailed information for debugging
    - INFO: General information about application flow (default)
    - WARNING: Warnings about potential issues
    - ERROR: Error messages for serious problems
    - CRITICAL: Critical errors that may stop the application
    
    The application will display configuration information at startup, including:
    - Log level and configuration source
    - Config file location
    - Cache directory path
    """
    root = tk.Tk()
    IODExplorer(root)
    root.mainloop()


if __name__ == "__main__":
    main()
