"""DCMSPEC Explorer - GUI application for dcmspec.

This module provides a graphical user interface for exploring DICOM specifications,
allowing users to browse IODs, modules, and attributes through an interactive interface.
"""

import tkinter as tk
from tkinter import ttk, messagebox, scrolledtext
import tkinter.font as tkfont
from typing import List, Tuple
import re
import logging
from anytree import PreOrderIter

from dcmspec.config import Config
from dcmspec.iod_spec_builder import IODSpecBuilder
from dcmspec.spec_factory import SpecFactory
from dcmspec.xhtml_doc_handler import XHTMLDocHandler
from dcmspec.dom_table_spec_parser import DOMTableSpecParser


def load_app_config() -> Config:
    """Load app-specific configuration with priority search order.
    
    Search order:
    1. App-specific config files (dcmspec_explorer_config.json) - Tier 1
       - Current directory
       - ~/.config/dcmspec/
       - App config directory (src/dcmspec/apps/dcmspec_explorer/config/)
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
        "dcmspec_explorer_config.json",  # Current directory
        os.path.expanduser("~/.config/dcmspec/dcmspec_explorer_config.json"),  # User config
        os.path.join(os.path.dirname(__file__), "config", "dcmspec_explorer_config.json"),  # App config dir
        os.path.join(os.path.dirname(__file__), "dcmspec_explorer_config.json"),  # Same dir as script (legacy)
    ]
    
    config_file = None
    
    # First, check for app-specific config files
    for location in app_config_locations:
        if os.path.exists(location):
            config_file = location
            break
    
    # If no app-specific config found, let Config class use its default location
    # This will be: user_config_dir("dcmspec_explorer")/config.json
    config = Config(app_name="dcmspec_explorer", config_file=config_file)
    
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
    logger = logging.getLogger("dcmspec_explorer")
    
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


class DCMSpecExplorer:
    """Main window for the DCMSPEC Explorer application."""
    
    def __init__(self, root: tk.Tk):
        """Initialize the main window."""
        self.root = root
        self.root.title("DCMSPEC Explorer")
        
        # Load app-specific configuration
        self.config = load_app_config()
        
        # Initialize logger using configuration
        self.logger = setup_logger(self.config)
        
        # Log startup information
        self.logger.info("Starting DCMSPEC Explorer")
        
        # Log configuration information at INFO level
        log_level_configured = self.config.get_param('log_level') or 'INFO'
        config_source = ("app-specific" if self.config.config_file and 
                        "dcmspec_explorer_config.json" in self.config.config_file else "default")
        self.logger.info(f"Logging configured: level={log_level_configured.upper()}, source={config_source}")
        
        # Log operational configuration at INFO level (important for users to know)
        config_file_display = self.config.config_file or "none (using defaults)"
        self.logger.info(f"Config file: {config_file_display}")
        self.logger.info(f"Cache directory: {self.config.cache_dir}")
        
        # Initialize document handler
        self.doc_handler = XHTMLDocHandler(config=self.config, logger=self.logger)
        
        # Initialize DOM parser for version extraction
        self.dom_parser = DOMTableSpecParser(logger=self.logger)
        
        # Set window size and center it on screen
        window_width = 1000
        window_height = 700
        
        # Get screen dimensions
        screen_width = root.winfo_screenwidth()
        screen_height = root.winfo_screenheight()
        
        # Calculate position to center the window
        x = (screen_width - window_width) // 2
        y = (screen_height - window_height) // 2
        
        # Set geometry with centered position
        self.root.geometry(f"{window_width}x{window_height}+{x}+{y}")
        
        # URL for DICOM Part 3 Table of Contents
        self.part3_toc_url = "https://dicom.nema.org/medical/dicom/current/output/chtml/part03/ps3.3.html"
        
        # Store original data for sorting
        self.iod_modules_data = []
        self.sort_column = None
        self.sort_reverse = False
        
        # Store IOD models to keep AnyTree nodes in memory
        self.iod_models = {}  # table_id -> model mapping
        
        # Store DICOM version
        self.dicom_version = "Unknown"
        
        self.setup_ui()
        self.load_iod_modules()
    
    def setup_ui(self):
        """Set up the user interface."""
        # Create main frame
        main_frame = ttk.Frame(self.root)
        main_frame.pack(fill=tk.BOTH, expand=True, padx=10, pady=10)
        
        # Create top frame for controls
        top_frame = ttk.Frame(main_frame)
        top_frame.pack(fill=tk.X, pady=(0, 10))
        
        # Add title label
        title_label = ttk.Label(top_frame, text="DICOM IOD List", font=("Arial", 16, "bold"))
        title_label.pack(side=tk.LEFT)
        
        # Add refresh button with context menu option
        refresh_btn = ttk.Button(top_frame, text="Reload", command=self.load_iod_modules)
        refresh_btn.pack(side=tk.RIGHT)
        
        # Add version label to the left of the button with right justification and spacing
        self.version_label = ttk.Label(top_frame, text="", font=("Arial", 10), anchor="e")
        self.version_label.pack(side=tk.RIGHT, padx=(0, 10))
        
        # Add context menu for refresh button
        self._create_refresh_context_menu(refresh_btn)
        
        # Create paned window for treeview and details
        paned_window = ttk.PanedWindow(main_frame, orient=tk.HORIZONTAL)
        paned_window.pack(fill=tk.BOTH, expand=True)
        
        # Left frame for treeview
        left_frame = ttk.Frame(paned_window)
        paned_window.add(left_frame, weight=1)
        
        # Create treeview
        tree_frame = ttk.Frame(left_frame)
        tree_frame.pack(fill=tk.BOTH, expand=True)
        
        # Treeview with scrollbar - configure with monospaced font for better tag display
        self.tree = ttk.Treeview(
            tree_frame, 
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
        
        # Verify the configuration
        actual_font = style.lookup("Treeview", "font")
        self.logger.debug(f"Final font configuration: {actual_font}")
        self.tree.heading("#0", text="IOD Name", command=lambda: self.sort_treeview("#0"))
        self.tree.heading("iod_type", text="IOD Type", command=lambda: self.sort_treeview("iod_type"))
        self.tree.heading("usage", text="Usage")  # No sorting command
        self.tree.column("#0", width=400)
        self.tree.column("iod_type", width=100)
        self.tree.column("usage", width=80)
        
        # Scrollbars for treeview
        tree_scroll_y = ttk.Scrollbar(tree_frame, orient=tk.VERTICAL, command=self.tree.yview)
        tree_scroll_x = ttk.Scrollbar(tree_frame, orient=tk.HORIZONTAL, command=self.tree.xview)
        self.tree.configure(yscrollcommand=tree_scroll_y.set, xscrollcommand=tree_scroll_x.set)
        
        self.tree.pack(side=tk.LEFT, fill=tk.BOTH, expand=True)
        tree_scroll_y.pack(side=tk.RIGHT, fill=tk.Y)
        tree_scroll_x.pack(side=tk.BOTTOM, fill=tk.X)
        
        # Right frame for details
        right_frame = ttk.Frame(paned_window)
        paned_window.add(right_frame, weight=1)
        
        # Details text area
        details_label = ttk.Label(right_frame, text="Details", font=("Arial", 12, "bold"))
        details_label.pack(anchor=tk.W, pady=(0, 5))
        
        self.details_text = scrolledtext.ScrolledText(right_frame, wrap=tk.WORD, width=50, height=30)
        self.details_text.pack(fill=tk.BOTH, expand=True)
        
        # Bind treeview selection event
        self.tree.bind("<<TreeviewSelect>>", self.on_tree_select)
        
        # Status bar
        self.status_var = tk.StringVar()
        self.status_var.set("Ready")
        status_bar = ttk.Label(main_frame, textvariable=self.status_var, relief=tk.SUNKEN)
        status_bar.pack(fill=tk.X, side=tk.BOTTOM, pady=(5, 0))
    
    def _create_refresh_context_menu(self, refresh_btn):
        """Create a context menu for the refresh button."""
        context_menu = tk.Menu(self.root, tearoff=0)
        context_menu.add_command(label="Reload (from cache)", command=self.load_iod_modules)
        context_menu.add_command(label="Download latest (from web)", 
                               command=lambda: self.load_iod_modules(force_download=True))
        
        def show_context_menu(event):
            try:
                context_menu.tk_popup(event.x_root, event.y_root)
            finally:
                context_menu.grab_release()
        
        # Add tooltip to explain the context menu
        def create_tooltip():
            tooltip = tk.Toplevel(self.root)
            tooltip.wm_overrideredirect(True)
            tooltip.wm_geometry("+%d+%d" % (refresh_btn.winfo_rootx(), 
                                          refresh_btn.winfo_rooty() + refresh_btn.winfo_height() + 5))
            label = ttk.Label(tooltip, text="Right-click for more options", 
                            background="lightyellow", relief=tk.SOLID, borderwidth=1)
            label.pack()
            tooltip.after(2000, tooltip.destroy)  # Auto-hide after 2 seconds
        
        # Bind events
        refresh_btn.bind("<Button-2>", show_context_menu)  # Middle click
        refresh_btn.bind("<Button-3>", show_context_menu)  # Right click
        refresh_btn.bind("<Control-Button-1>", show_context_menu)  # Ctrl+Left click (alternative)
        
        # Show tooltip on hover (to help users discover the context menu)
        def on_enter(event):
            refresh_btn.after(1000, create_tooltip)  # Show tooltip after 1 second hover
        
        def on_leave(event):
            refresh_btn.after_cancel(refresh_btn.after_idle(lambda: None))  # Cancel tooltip
        
        refresh_btn.bind("<Enter>", on_enter)
        refresh_btn.bind("<Leave>", on_leave)
    
    def load_iod_modules(self, force_download: bool = False):
        """Load IOD modules from the DICOM specification.
        
        Args:
            force_download (bool): If True, force download from URL instead of using cache.
            
        """
        self.status_var.set("Loading IOD modules...")
        self.root.update()
        
        try:
            # Clear existing items
            for item in self.tree.get_children():
                self.tree.delete(item)
            
            # Use XHTMLDocHandler to download and parse the HTML with caching
            cache_file_name = "ps3.3.html"
            soup = self.doc_handler.load_document(
                cache_file_name=cache_file_name,
                url=self.part3_toc_url,
                force_download=force_download
            )
            
            # Extract and display DICOM version using the library method
            self.dicom_version = self.dom_parser.get_version(soup, "")
            self.version_label.config(text=f"Version {self.dicom_version}")
            
            # Find the list of tables div
            list_of_tables = soup.find('div', class_='list-of-tables')
            if not list_of_tables:
                messagebox.showerror("Error", "Could not find list-of-tables section")
                return
            
            # Extract IOD modules
            iod_modules = self.extract_iod_modules(list_of_tables)
            
            # Store the data for sorting
            self.iod_modules_data = iod_modules
            
            # Set initial sort state to show that data is sorted by IOD Name
            self.sort_column = "#0"
            self.sort_reverse = False
            
            # Populate treeview
            self.populate_treeview(iod_modules)
            
            # Update column headings to show initial sort state
            self.update_column_headings()
            
            cache_status = " (downloaded)" if force_download else " (from cache)"
            self.status_var.set(f"Loaded {len(iod_modules)} IOD modules{cache_status}")
            
        except RuntimeError as e:
            messagebox.showerror("Error", f"Failed to load DICOM specification:\n{str(e)}")
            self.status_var.set("Error loading modules")
        except Exception as e:
            messagebox.showerror("Error", f"An error occurred:\n{str(e)}")
            self.status_var.set("Error loading modules")
    
    def extract_iod_modules(self, list_of_tables) -> List[Tuple[str, str, str, str]]:
        """Extract IOD modules from the list of tables section.
        
        Returns:
            List of tuples (title, table_id, href, iod_type)
            
        """
        iod_modules = []
        
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
                    if title.endswith(" IOD Modules"):
                        title = title[:-12]  # Remove " IOD Modules" (12 characters)
                    
                    # Determine IOD type based on table_id
                    if "_A." in table_id:
                        iod_type = "Composite"
                    elif "_B." in table_id:
                        iod_type = "Normalized"
                    else:
                        iod_type = "Other"
                    
                    iod_modules.append((title, table_id, href, iod_type))
        
        return sorted(iod_modules, key=lambda x: x[0])
    
    def populate_treeview(self, iod_modules: List[Tuple[str, str, str, str]]):
        """Populate the treeview with IOD modules."""
        for title, table_id, href, iod_type in iod_modules:
            # Store table_id in tags for later retrieval, display iod_type in column
            self.tree.insert("", tk.END, text=title, values=(iod_type, ""), 
                           tags=(table_id,))
    
    def sort_treeview(self, column: str):
        """Sort the treeview by the specified column."""
        # Determine if we need to reverse the sort
        if self.sort_column == column:
            self.sort_reverse = not self.sort_reverse
        else:
            self.sort_reverse = False
        
        self.sort_column = column
        
        # Sort the data
        if column == "#0":  # IOD Name column
            sorted_data = sorted(self.iod_modules_data, 
                                key=lambda x: x[0].lower(), 
                                reverse=self.sort_reverse)
        elif column == "iod_type":  # IOD Type column
            sorted_data = sorted(self.iod_modules_data, 
                                key=lambda x: x[3].lower(), 
                                reverse=self.sort_reverse)
        else:
            # Unknown column, keep original order
            sorted_data = self.iod_modules_data
        
        # Clear the treeview
        for item in self.tree.get_children():
            self.tree.delete(item)
        
        # Repopulate with sorted data
        self.populate_treeview(sorted_data)
        
        # Update column headings to show sort direction
        self.update_column_headings()
    
    def update_column_headings(self):
        """Update column headings to show sort direction."""
        # Reset all headings
        self.tree.heading("#0", text="IOD Name")
        self.tree.heading("iod_type", text="IOD Type")
        self.tree.heading("usage", text="Usage")
        
        # Add sort indicator to the current sort column
        if self.sort_column:
            indicator = " ↓" if self.sort_reverse else " ↑"
            if self.sort_column == "#0":
                self.tree.heading("#0", text=f"IOD Name{indicator}")
            elif self.sort_column == "iod_type":
                self.tree.heading("iod_type", text=f"IOD Type{indicator}")
    
    def on_tree_select(self, event):
        """Handle treeview selection event."""
        selection = self.tree.selection()
        if not selection:
            return
        
        item = selection[0]
        item_values = self.tree.item(item, "values")
        title = self.tree.item(item, "text")
        tags = self.tree.item(item, "tags")
        
        # Check if this is a top-level IOD item (has table_id in tags)
        # Top-level IOD items have table_id starting with "table_", 
        # while modules/attributes have AnyTree node objects
        if tags and len(tags) > 0 and isinstance(tags[0], str) and tags[0].startswith("table_"):
            # This is a top-level IOD item
            table_id = tags[0]
            iod_type = item_values[0] if item_values else "Unknown"
            
            # Check if this item already has children (IOD structure loaded)
            if self.tree.get_children(item):
                # Already loaded, just update details
                self._update_details_text(table_id, title, iod_type)
                return
            
            # Build the IOD model and populate the tree structure
            try:
                self.status_var.set(f"Loading IOD structure for {table_id}...")
                self.root.update()
                
                # Build the IOD model using the same logic as iodattributes.py
                model = self._build_iod_model(table_id)
                
                # Store the model to keep AnyTree nodes in memory
                self.iod_models[table_id] = model
                
                if model and hasattr(model, 'content') and model.content:
                    # Populate the tree item with the IOD structure
                    self._populate_iod_structure(item, model.content)
                    
                    # Expand the item to show the structure
                    self.tree.item(item, open=True)
                
                self._update_details_text(table_id, title, iod_type)
                self.status_var.set(f"Loaded structure for {table_id}")
                
            except RuntimeError as e:
                error_msg = str(e)
                if "No module models were found" in error_msg:
                    detailed_msg = (f"Failed to load IOD structure for {title}:\n\n"
                                  f"The IOD references modules that could not be found or parsed. "
                                  f"This may happen if:\n"
                                  f"• Module reference tables are missing from the DICOM specification\n"
                                  f"• Module tables have different naming conventions\n"
                                  f"• The IOD table format is not supported\n\n"
                                  f"Technical details: {error_msg}")
                    messagebox.showwarning("IOD Structure Not Available", detailed_msg)
                    self.logger.warning(f"Failed to build IOD model for {table_id}: {error_msg}")
                else:
                    messagebox.showerror("Error", f"Failed to load IOD structure:\n{error_msg}")
                self.status_var.set(f"Could not load structure for {table_id}")
                self._update_details_text(table_id, title, iod_type)
            except Exception as e:
                messagebox.showerror("Error", f"Failed to load IOD structure:\n{str(e)}")
                self.status_var.set(f"Error loading {table_id}")
                self._update_details_text(table_id, title, iod_type)
        
        else:
            # This is a module or attribute item
            node_type = item_values[0] if item_values else "Unknown"
            usage = item_values[1] if len(item_values) > 1 else ""
            
            # Get AnyTree node using the node path stored in tags
            node = None
            if tags and len(tags) > 0:
                node_path = tags[0]
                # Find the node by traversing the path in the appropriate IOD model
                # First, determine which IOD model this node belongs to by checking parent items
                current_item = item
                table_id = None
                
                # Walk up the tree to find the root IOD item
                while current_item:
                    parent_item = self.tree.parent(current_item)
                    if not parent_item:  # This is a root item
                        item_tags = self.tree.item(current_item, "tags")
                        if item_tags and item_tags[0].startswith("table_"):
                            table_id = item_tags[0]
                        break
                    current_item = parent_item
                
                # Get the node from the IOD model using the path
                if table_id and table_id in self.iod_models:
                    model = self.iod_models[table_id]
                    if model and hasattr(model, 'content') and model.content:
                        # Find the node by path
                        try:
                            # Split the path and traverse to find the node
                            path_parts = node_path.split("/")
                            current_node = model.content
                            
                            # Navigate through the path (skip the first part which is the root)
                            for part in path_parts[1:]:  
                                found = False
                                for child in current_node.children:
                                    if str(child.name) == part:
                                        current_node = child
                                        found = True
                                        break
                                if not found:
                                    break
                            else:
                                # Successfully found the node
                                node = current_node
                        except Exception as e:
                            self.logger.debug(f"Error finding node at path {node_path}: {e}")
            
            # Update details text for module/attribute

            if node_type == "Module" and node:
                # Get all available module attributes
                name = getattr(node, 'module', 'Unknown Module')
                usage = getattr(node, 'usage', '')
                module_ref = getattr(node, 'ref', '')
                ie = getattr(node, 'ie', '')

                details = f"{name} {node_type}\n\n"

                if ie:
                    details += f"Information Entity: {ie}\n"

                if usage:
                    # Format usage as a single line with description and code
                    if usage.startswith("M"):
                        usage_display = "Mandatory (M)"
                    elif usage.startswith("U"):
                        usage_display = "User Optional (U)"
                    elif usage.startswith("C"):
                        # For conditional, include the conditional statement
                        if len(usage) > 1 and " - " in usage:
                            conditional_part = usage[usage.find(" - ") + 3:]
                            usage_display = f"Conditional (C) - {conditional_part}"
                        else:
                            usage_display = "Conditional (C)"
                    else:
                        usage_display = usage
                    
                    details += f"Usage: {usage_display}\n"
                
                if module_ref:
                    details += f"Reference: {module_ref}\n"

            elif node_type == "Attribute" and node:
                # Get all available attribute details from the node
                elem_name = getattr(node, 'elem_name', 'Unknown')
                elem_tag = getattr(node, 'elem_tag', '')
                elem_type = getattr(node, 'elem_type', '')
                elem_description = getattr(node, 'elem_description', '')
                
                # Display all available attribute information
                details = f"{elem_name} {node_type}\n\n"

                if elem_tag:
                    details += f"Tag: {elem_tag}\n"
                if elem_type:
                    details += f"Type: {elem_type}\n"
                if elem_description:
                    details += f"Description: {elem_description}\n"
            else:
                # Fallback for cases without node reference
                if usage:
                    details += f"Usage/Type: {usage}\n"
                
            self.details_text.delete(1.0, tk.END)
            self.details_text.insert(1.0, details)
            
            self.status_var.set(f"Selected: {node_type} - {title}")
    
    def _build_iod_model(self, table_id: str):
        """Build the IOD model for the given table_id."""
        url = "https://dicom.nema.org/medical/dicom/current/output/html/part03.html"
        cache_file_name = "Part3.xhtml"
        model_file_name = f"Part3_{table_id}_expanded.json"
        
        # Determine if this is a composite or normalized IOD
        composite_iod = "_A." in table_id
        
        # Create the IOD specification factory
        c_iod_columns_mapping = {0: "ie", 1: "module", 2: "ref", 3: "usage"}
        n_iod_columns_mapping = {0: "module", 1: "ref", 2: "usage"}
        iod_columns_mapping = c_iod_columns_mapping if composite_iod else n_iod_columns_mapping
        iod_factory = SpecFactory(
            column_to_attr=iod_columns_mapping, 
            name_attr="module",
            config=self.config,
            logger=self.logger,
        )
        
        # Create the modules specification factory
        parser_kwargs = None if composite_iod else {"skip_columns": [2]}
        module_factory = SpecFactory(
            column_to_attr={0: "elem_name", 1: "elem_tag", 2: "elem_type", 3: "elem_description"},
            name_attr="elem_name",
            parser_kwargs=parser_kwargs,
            config=self.config,
            logger=self.logger,
        )
        
        # Create the builder
        builder = IODSpecBuilder(
            iod_factory=iod_factory, 
            module_factory=module_factory,
            logger=self.logger,
        )
        
        # Build and return the model
        return builder.build_from_url(
            url=url,
            cache_file_name=cache_file_name,
            json_file_name=model_file_name,
            table_id=table_id,
            force_download=False,
        )
    
    def _populate_iod_structure(self, parent_item, content):
        """Populate the tree with IOD structure from the model content using AnyTree traversal."""
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
                # This is a module node
                module_name = getattr(node, 'module', 'Unknown Module')
                
                display_text = module_name
                node_type = "Module"
                
                # For normalized IODs, modules don't have usage information
                # Check if this is a normalized IOD from the parent item's IOD type
                parent_values = self.tree.item(parent_item, "values") if parent_item else None
                is_normalized = parent_values and len(parent_values) > 0 and parent_values[0] == "Normalized"
                
                if is_normalized:
                    usage = ""  # No usage for normalized IOD modules
                else:
                    usage = getattr(node, 'usage', '')[:1]  # Keep only the first character for composite IODs
                
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
                values=(node_type, usage), tags=(node_path,)
            )
            tree_items[node] = tree_item
    
    def _update_details_text(self, table_id: str, title: str, iod_type: str):
        """Update the details text area."""
        details = f"{title} {iod_type} IOD\n\n"
        details += f"Table ID: {table_id}\n\n"
        
        # Check if we have a model for this IOD
        if table_id in self.iod_models and self.iod_models[table_id] and hasattr(self.iod_models[table_id], 'content'):
            details += "Click to expand and view the IOD structure with modules and attributes."
        else:
            details += ("IOD structure not available. This may occur if the IOD references modules "
                       "that cannot be found or parsed from the DICOM specification.")
        
        self.details_text.delete(1.0, tk.END)
        self.details_text.insert(1.0, details)
        
        self.status_var.set(f"Selected: {title} {iod_type} IOD)")


def main() -> None:
    """Entry point for the DCMSPEC Explorer GUI application.
    
    Loads configuration and starts the GUI. Configuration can be customized
    by placing a dcmspec_explorer_config.json file in:
    1. Current directory
    2. ~/.config/dcmspec/
    3. App config directory (src/dcmspec/apps/dcmspec_explorer/config/)
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
    DCMSpecExplorer(root)
    root.mainloop()


if __name__ == "__main__":
    main()
