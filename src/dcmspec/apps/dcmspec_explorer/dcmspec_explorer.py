"""DCMspec Explorer - GUI application for dcmspec.

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

from dcmspec.config import Config
from dcmspec.iod_spec_builder import IODSpecBuilder
from dcmspec.spec_factory import SpecFactory
from dcmspec.xhtml_doc_handler import XHTMLDocHandler
from dcmspec.dom_table_spec_parser import DOMTableSpecParser


class StatusManager:
    """Handles status bar messaging with consistent logic."""
    
    def __init__(self, status_var):
        """Initialize the StatusManager.

        Args:
            status_var: A tkinter StringVar or similar object used to update the status bar text.

        """
        self.status_var = status_var
    
    def show_count_status(self, filtered_count: int, total_count: int, 
                            is_favorites_mode: bool = False, is_filtered: bool = False,
                            favorites_count: int = 0, cache_suffix: str = ""):
        """Show count-based status when no selection."""
        if is_filtered:
            message = f"Showing {filtered_count} of {total_count} IODs (filtered)"
        else:
            message = f"Showing {filtered_count} IODs"

        self.status_var.set(f"{message}{cache_suffix}")
    
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

    config_file = next(
        (
            location
            for location in app_config_locations
            if os.path.exists(location)
        ),
        None,
    )
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
    """Main window for the DCMspec Explorer application."""

    def __init__(self, root: tk.Tk):
        """Initialize the DCMspec Explorer application.

        This method initializes the backend services and domain model, as well as the frontend controllers and views.
        """
        # --- Backend Services ---

        # Load app-specific configuration
        self.config = load_app_config()
        # Initialize logger using configuration
        self.logger = setup_logger(self.config)

        # Log startup information
        self.logger.info("Starting DCMspec Explorer")
        # Log configuration information at INFO level
        log_level_configured = self.config.get_param('log_level') or 'INFO'
        config_source = ("app-specific" if self.config.config_file and 
                        "dcmspec_explorer_config.json" in self.config.config_file else "default")
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
        self.part3_toc_url = "https://dicom.nema.org/medical/dicom/current/output/chtml/part03/ps3.3.html"
        # Initialize list of all IODs (original, unsorted/filtered)
        self.iod_modules_data = []
        self.sort_column = None
        self.sort_reverse = False
        # Initialize list of filtered IODs for display (populated after filtering)
        self.filtered_data = []
        self.search_text = ""
        # Store IOD models to keep AnyTree nodes in memory
        self.iod_models = {}  # table_id -> model mapping
        # Store DICOM version
        self.dicom_version = "Unknown"

        # --- Frontend State / Controller ---

        # --- View ---

        self.root = root
        self.root.title("DCMspec Explorer")
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
        
        # Create top frame for controls
        top_frame = ttk.Frame(main_frame)
        top_frame.pack(fill=tk.X, pady=(0, 10))
        
        # Configure grid columns: column 0 (search) gets all extra space, column 1 (controls) stays minimal
        top_frame.columnconfigure(0, weight=1)  # Search area expands
        top_frame.columnconfigure(1, weight=0)  # Controls area stays fixed
        
        # Create search controls frame (left side, column 0)
        search_controls_frame = ttk.Frame(top_frame)
        search_controls_frame.grid(row=0, column=0, sticky="ew", padx=(0, 20))
        
        # Add search label and entry
        search_label = ttk.Label(search_controls_frame, text="Search:")
        search_label.pack(side=tk.LEFT, padx=(0, 5))
        
        self.search_var = tk.StringVar()
        self.search_var.trace_add('write', self.on_search_changed)
        search_entry = ttk.Entry(search_controls_frame, textvariable=self.search_var, width=30)
        search_entry.pack(side=tk.LEFT, padx=(0, 20))
        
        # Create right controls frame (column 1)
        controls_frame = ttk.Frame(top_frame)
        controls_frame.grid(row=0, column=1, sticky="e")
        
        # Add version label to the left of the button with right justification and spacing
        self.version_label = ttk.Label(controls_frame, text="", font=("Arial", 10), anchor="e")
        self.version_label.pack(side=tk.LEFT, padx=(0, 10))
        
        # Add refresh button with context menu option
        refresh_btn = ttk.Button(controls_frame, text="Reload", command=self.load_iod_modules)
        refresh_btn.pack(side=tk.LEFT)
        
        # Add context menu for refresh button
        self._create_refresh_context_menu(refresh_btn)
        
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
        self.tree.heading("#0", text="Name", command=lambda: self.sort_treeview("#0"))
        self.tree.heading("iod_type", text="Kind", command=lambda: self.sort_treeview("iod_type"))
        self.tree.heading("usage", text="")  # No sorting command
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

    def on_search_changed(self, *args):
        """Handle search text change."""
        self.search_text = self.search_var.get()  # Remove .lower() to make case sensitive
        self.apply_filter_and_sort()
    
    def apply_filter_and_sort(self):
        """Apply current search filter and sort to the data."""
        # Remember current selection before clearing
        current_selection_table_id = None
        selection = self.tree.selection()
        if selection:
            selected_item = selection[0]
            tags = self.tree.item(selected_item, "tags")
            if tags and len(tags) > 0 and isinstance(tags[0], str) and tags[0].startswith("table_"):
                current_selection_table_id = tags[0]

        # Start with original data
        data = self.iod_modules_data

        # Apply search filter if there's search text
        if self.search_text:
            filtered_data = []
            filtered_data.extend(
                (title, table_id, href, iod_type)
                for title, table_id, href, iod_type in data
                if (self.search_text in title or self.search_text in iod_type)
            )
            data = filtered_data

        self.filtered_data = data

        # Apply current sort if any
        if self.sort_column:
            if self.sort_column == "#0":  # IOD Name column
                data = sorted(data, key=lambda x: x[0].lower(), reverse=self.sort_reverse)
            elif self.sort_column == "iod_type":  # IOD Type column
                data = sorted(data, key=lambda x: x[3].lower(), reverse=self.sort_reverse)

        # Clear the treeview
        for item in self.tree.get_children():
            self.tree.delete(item)

        # Repopulate with filtered and sorted data
        self.populate_treeview(data)

        # Restore IOD structures for any IODs that were previously loaded
        for item in self.tree.get_children():
            tags = self.tree.item(item, "tags")
            if tags and len(tags) > 0 and isinstance(tags[0], str) and tags[0].startswith("table_"):
                table_id = tags[0]
                # If we have a model for this IOD, restore its structure
                if table_id in self.iod_models and self.iod_models[table_id]:
                    model = self.iod_models[table_id]
                    if model and hasattr(model, 'content') and model.content:
                        # Repopulate the IOD structure
                        self._populate_iod_structure(item, model.content)
                        # Don't auto-expand - let user decide when to expand

        # Restore selection if the previously selected item is still visible
        if current_selection_table_id:
            for item in self.tree.get_children():
                tags = self.tree.item(item, "tags")
                if tags and len(tags) > 0 and tags[0] == current_selection_table_id:
                    self.tree.selection_set(item)
                    self.tree.focus(item)
                    # Scroll to make the selected item visible
                    self.tree.see(item)
                    # Trigger the selection event to update details
                    self.on_tree_select(None)
                    break
        else:
            self.details_text.set_html(
                f'<div style="font-family: {self.details_font_family}; font-size: {self.details_font_size}px;">'
                f'<span>Select an IOD to view details.</span><br>'
                f'</div>'
)

        # Update status
        total_count = len(self.iod_modules_data)
        filtered_count = len(data)

        # Use StatusManager for consistent status messages
        self.status_manager.show_count_status(
            filtered_count=filtered_count,
            total_count=total_count,
            is_favorites_mode=False,
            is_filtered=bool(self.search_text),
            favorites_count=0,
            cache_suffix=""
        )

    def load_iod_modules(self, force_download: bool = False):
        """Load IOD modules from the DICOM specification.

        Args:
            force_download (bool): If True, force download from URL instead of using cache.

        """
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
                force_download=force_download,
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

            # Extract IOD modules
            iod_modules = self.extract_iod_modules(list_of_tables)

            # Store the data for sorting and filtering
            self.iod_modules_data = iod_modules

            # Set initial sort state to show that data is sorted by IOD Name
            self.sort_column = "#0"
            self.sort_reverse = False

            # Apply filter and sort (this will populate the treeview)
            self.apply_filter_and_sort()

            # Update column headings to show initial sort state
            self.update_column_headings()

            # Add cache status to the current status (after apply_filter_and_sort sets it)
            cache_status = " (downloaded)" if force_download else " (from cache)"
            current_status = self.status_var.get()
            self.status_var.set(f"{current_status}{cache_status}")

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
            self.tree.insert("", tk.END, text=title, values=(iod_type, ""), 
                            tags=(table_id, iod_type))

    def sort_treeview(self, column: str):
        """Sort the treeview by the specified column."""
        # Determine if we need to reverse the sort
        if self.sort_column == column:
            self.sort_reverse = not self.sort_reverse
        else:
            self.sort_reverse = False
        
        self.sort_column = column
        
        # Apply filter and sort (this will update the treeview)
        self.apply_filter_and_sort()
        
        # Update column headings to show sort direction
        self.update_column_headings()

    def update_column_headings(self):
        """Update column headings to show sort direction."""
        # Reset all headings
        self.tree.heading("#0", text="Name")
        self.tree.heading("iod_type", text="Kind")
        self.tree.heading("usage", text="")
        
        # Add sort indicator to the current sort column
        if self.sort_column:
            indicator = " ↓" if self.sort_reverse else " ↑"
            if self.sort_column == "#0":
                self.tree.heading("#0", text=f"Name{indicator}")
            elif self.sort_column == "iod_type":
                self.tree.heading("iod_type", text=f"Kind{indicator}")

    def _is_model_cached(self, table_id: str) -> bool:
        """Check if the IOD model is already cached on disk."""
        model_file_name = f"Part3_{table_id}_expanded.json"
        cache_file_path = os.path.join(self.config.cache_dir, "model", model_file_name)
        exists = os.path.exists(cache_file_path)
        return exists

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
            iod_type = tags[1] if len(tags) > 1 else "Unknown"

            # Update status
            self.status_manager.show_selection_status(title, iod_type, is_iod=True)

            # Check if we already have the structure loaded in memory
            if table_id in self.iod_models and self.iod_models[table_id]:
                # Already in memory - just update details
                self._update_details_text(table_id, title, iod_type)
                return

            # Check if model is cached on disk
            if self._is_model_cached(table_id):
                # Cached - load immediately without progress dialog
                try:
                    self.status_manager.show_loading_status(f"Loading {title} from cache...")
                    self.root.update()  # Update UI to show status

                    # Use the API directly since it's cached - should be fast
                    model = self._build_iod_model(table_id, self.logger)

                    if model:
                        # Store the model to keep AnyTree nodes in memory
                        self.iod_models[table_id] = model

                        if model.content:
                            # Populate the tree item with the IOD structure
                            self._populate_iod_structure(item, model.content)

                            # Expand the item to show the structure
                            # self.tree.item(item, open=True)

                        self._update_details_text(table_id, title, iod_type)
                        # Update status for successful IOD selection
                        self.status_manager.show_selection_status(title, iod_type, is_iod=True)

                except Exception as e:
                    # Handle errors for cached loading
                    if "No module models were found" in str(e):
                        detailed_msg = (f"Failed to load IOD structure for {title}:\n\n"
                                        f"The IOD references modules that could not be found or parsed. "
                                        f"This may happen if:\n"
                                        f"• Module reference tables are missing from the DICOM specification\n"
                                        f"• Module tables have different naming conventions\n"
                                        f"• The IOD table format is not supported\n\n"
                                        f"Technical details: {str(e)}")
                        messagebox.showwarning("IOD Structure Not Available", detailed_msg)
                        self.logger.warning(f"Failed to build IOD model for {table_id}: {str(e)}")
                    else:
                        messagebox.showerror("Error", f"Failed to load IOD structure:\n{str(e)}")

                    self._update_details_text(table_id, title, iod_type)
                    # Update status for IOD selection even when there's an error
                    self.status_manager.show_selection_status(title, iod_type, is_iod=True)
            else:
                # Not cached - load directly (will freeze UI briefly)
                try:
                    self.status_manager.show_loading_status(f"Loading {title} (this may take a moment)...")
                    self.root.update()  # Update UI to show status
                    
                    # Build directly without progress dialog
                    model = self._build_iod_model(table_id, self.logger)
                    
                    if model:
                        # Store the model to keep AnyTree nodes in memory
                        self.iod_models[table_id] = model
                        
                        if model.content:
                            # Populate the tree item with the IOD structure
                            self._populate_iod_structure(item, model.content)
                        
                        self._update_details_text(table_id, title, iod_type)
                        # Update status for successful IOD selection
                        self.status_manager.show_selection_status(title, iod_type, is_iod=True)
                        
                except Exception as e:
                    # Handle building errors
                    if "No module models were found" in str(e):
                        detailed_msg = (f"Failed to load IOD structure for {title}:\n\n"
                                        f"The IOD references modules that could not be found or parsed. "
                                        f"This may happen if:\n"
                                        f"• Module reference tables are missing from the DICOM specification\n"
                                        f"• Module tables have different naming conventions\n"
                                        f"• The IOD table format is not supported\n\n"
                                        f"Technical details: {str(e)}")
                        messagebox.showwarning("IOD Structure Not Available", detailed_msg)
                        self.logger.warning(f"Failed to build IOD model for {table_id}: {str(e)}")
                    else:
                        messagebox.showerror("Error", f"Failed to load IOD structure:\n{str(e)}")

                    self._update_details_text(table_id, title, iod_type)
                    # Update status for IOD selection even when there's an error
                    self.status_manager.show_selection_status(title, iod_type, is_iod=True)

        else:
            # This is a module or attribute item
            node_type = item_values[0] if len(item_values) > 0 else "Unknown"  # Changed from index 1 to 0
            usage = item_values[1] if len(item_values) > 1 else ""  # Changed from index 2 to 1

            # Get the corresponding AnyTree node using the node path stored in tags
            node = None
            if tags and len(tags) > 0:
                node_path = tags[0]
                # Find the node by traversing the path in the appropriate IOD model
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
                                # Build readable path for status bar
                                readable_path = self._build_readable_path(node)
                        except Exception as e:
                            self.logger.debug(f"Error finding node at path {node_path}: {e}")

            # Update details text for module/attribute
            if node_type == "Module" and node:
                # Get all available module attributes
                name = getattr(node, 'module', 'Unknown Module')
                usage = getattr(node, 'usage', '')
                module_ref = getattr(node, 'ref', '')
                ie = getattr(node, 'ie', '')

                details = f"<h2>{name} {node_type}</h2>"

                if ie:
                    details += f"<span><b>Information Entity:</b> {ie}</span><br>"

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

                    details += f"<span><b>Usage:</b> {usage_display}</span><br>"

                if module_ref:
                    details += f"<span><b>Reference:</b> {module_ref}</span><br>"

            elif node_type == "Attribute" and node:
                # Get all available attribute details from the node
                elem_name = getattr(node, 'elem_name', 'Unknown')
                elem_tag = getattr(node, 'elem_tag', '')
                elem_type = getattr(node, 'elem_type', '')
                elem_description = getattr(node, 'elem_description', '')

                # Display all available attribute information
                details = f"<h2>{elem_name} {node_type}</h2>"

                if elem_tag:
                    details += f"<span><b>Tag:</b> {elem_tag}</span><br>"
                if elem_type:
                    # Map DICOM attribute types to meaningful descriptions
                    type_map = {
                        "1": "Mandatory (1)",
                        "1C": "Conditional (1C)",
                        "2": "Mandatory, may be empty (2)",
                        "2C": "Conditional, may be empty (2C)",
                        "3": "Optional (3)",
                        "": "Unspecified"
                    }
                    type_display = type_map.get(elem_type, f"Other ({elem_type})") if elem_type else "Unspecified"
                    details += f"<span><b>Type:</b> {type_display}</span><br>"
                if elem_description:
                    details += f"{elem_description}"
            else:
                # Fallback for cases without node reference
                details = f"{title} {node_type}\n\n"
                details = f"<h2>{title} {node_type}</h2>"
                if usage:
                    details += f"<span><b>Usage/Type:</b> {usage}</span><br>"
                readable_path = title

            self.details_text.set_html(
                (
                    f'<div style="font-family: {self.details_font_family}; '
                    f'font-size: {self.details_font_size}px;">{details}</div>'
                )
            )

            self.status_var.set(f"Selected: {node_type} - {readable_path}")

    
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
            logger=logger,  # Use the custom logger for progress tracking
        )
        
        # Create the modules specification factory
        
        # Set unformatted to False for elem_description (column 3), others remain True
        parser_kwargs = {"unformatted": {0: True, 1: True, 2: True, 3: False}}
        if not composite_iod:
            parser_kwargs["skip_columns"] = [2]
        module_factory = SpecFactory(
            column_to_attr={0: "elem_name", 1: "elem_tag", 2: "elem_type", 3: "elem_description"},
            name_attr="elem_name",
            parser_kwargs=parser_kwargs,
            config=self.config,
            logger=logger,  # Use the custom logger for progress tracking
        )
        
        # Create the builder
        builder = IODSpecBuilder(
            iod_factory=iod_factory, 
            module_factory=module_factory,
            logger=logger,  # Use the custom logger for progress tracking
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
        """Build a human-readable path from the AnyTree node using display names."""
        path_parts = []
        
        # Walk up the tree from the current node to the root
        current = node
        while current and current.parent:  # Stop before the root content node
            if hasattr(current, 'module'):
                # This is a module node - use module name
                display_name = getattr(current, 'module', 'Unknown Module')
            elif hasattr(current, 'elem_name'):
                # This is an attribute node - use elem_name
                elem_name = getattr(current, 'elem_name', 'Unknown Attribute')
                display_name = re.sub(r'^(?:&gt;|>)+', '', elem_name)  # Remove leading > characters
            else:
                # Fallback to node name
                display_name = str(getattr(current, 'name', 'Unknown'))
            
            path_parts.insert(0, display_name)  # Insert at beginning to build path from root
            current = current.parent
        
        # Join with " > " separator for a readable hierarchical path
        return "/".join(path_parts)

def main() -> None:
    """Entry point for the DCMspec Explorer GUI application.
    
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
