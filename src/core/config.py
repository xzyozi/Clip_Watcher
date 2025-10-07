# Window sizes
SETTINGS_WINDOW_GEOMETRY = "450x550"
MAIN_WINDOW_GEOMETRY = "600x530"

# Padding
FRAME_PADDING = "10"
BUTTON_PADDING_X = 5
BUTTON_PADDING_Y = 5

# History settings
HISTORY_LIMIT_MIN = 10
HISTORY_LIMIT_MAX = 1000
HISTORY_LIMIT_INCREMENT = 10

# Define themes
THEMES = {
    "light": {
        # General colors
        "bg": "#FFFFFF",              # Main window background
        "fg": "#212121",              # Default foreground/text color

        # Selection colors
        "select_bg": "#E3F2FD",        # Background color for selected items in lists/text
        "select_fg": "#212121",        # Foreground color for selected items

        # Frame & Label colors
        "frame_bg": "#F5F5F5",         # Background for frames and group boxes
        "label_fg": "#757575",         # Labels and secondary text

        # Entry widgets (Text, Entry, Spinbox)
        "entry_bg": "#FFFFFF",         # Background for text entry widgets
        "entry_fg": "#212121",         # Text color for entry widgets

        # Button colors
        "button_bg": "#E0E0E0",        # Background for buttons
        "button_fg": "#212121",        # Text color for buttons

        # Listbox/Treeview colors
        "listbox_bg": "#FFFFFF",       # Background for lists and trees
        "listbox_fg": "#212121",       # Text color for lists and trees

        # Special colors
        "pinned_bg": "#FFF9C4",        # Background for pinned items in the history
        "highlight_bg": "#EEEEEE",

        # Menu colors
        "menu_bg": "#FFFFFF",         # Background for menus
        "menu_fg": "#212121",         # Text color for menus
        "active_menu_bg": "#E3F2FD",   # Background for active/hovered menu items
        "active_menu_fg": "#212121",   # Text color for active/hovered menu items
    },
    "dark": {
        # General colors
        "bg": "#2E2E2E",              # Main window background
        "fg": "#E0E0E0",              # Default foreground/text color

        # Selection colors
        "select_bg": "#4A4A4A",        # Background color for selected items
        "select_fg": "#FFFFFF",        # Foreground color for selected items

        # Frame & Label colors
        "frame_bg": "#242424",         # Background for frames and group boxes
        "label_fg": "#BDBDBD",         # Labels and secondary text

        # Entry widgets (Text, Entry, Spinbox)
        "entry_bg": "#3A3A3A",         # Background for text entry widgets
        "entry_fg": "#E0E0E0",         # Text color for entry widgets

        # Button colors
        "button_bg": "#4A4A4A",        # Background for buttons
        "button_fg": "#FFFFFF",        # Text color for buttons

        # Listbox/Treeview colors
        "listbox_bg": "#2E2E2E",       # Background for lists and trees
        "listbox_fg": "#E0E0E0",       # Text color for lists and trees

        # Special colors
        "pinned_bg": "#555555",        # Background for pinned items
        "highlight_bg": "#3C3C3C",

        # Menu colors
        "menu_bg": "#242424",         # Background for menus
        "menu_fg": "#E0E0E0",         # Text color for menus
        "active_menu_bg": "#4A4A4A",   # Background for active/hovered menu items
        "active_menu_fg": "#FFFFFF",   # Text color for active/hovered menu items
    }
}